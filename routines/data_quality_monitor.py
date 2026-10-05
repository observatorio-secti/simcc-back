"""
Módulo de Auditoria de Integridade e Variação dos Dados (ETL Data Quality Monitor)
iaPós / SIMCC - SENAI CIMATEC

Analisa a variação dos dados gerais antes e depois da carga de dados (ETL).
Quando detecta qualquer não conformidade (queda inesperada de registros, tabelas zeradas,
perda de vínculos docente-programa, etc.), gera relatório detalhado e dispara e-mail de alerta.

Uso:
  python routines/data_quality_monitor.py --snapshot   (ou 'pre'  : salva snapshot pré-carga)
  python routines/data_quality_monitor.py --audit      (ou 'post' : compara pós-carga e alerta)
  python routines/data_quality_monitor.py --status     (exibe contagem atual das tabelas)
  python routines/data_quality_monitor.py --test-email (testa envio SMTP)
  python routines/data_quality_monitor.py --simulate   (simula anomalia para teste de e-mail)
"""

import argparse
import datetime
import json
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Garante path raiz do projeto
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

conn = None
settings = None
logger_routine = None


def init_db_connection():
    global conn, settings, logger_routine
    if conn is not None:
        return conn, settings, logger_routine

    try:
        from simcc.core.config import settings as _settings
        from simcc.repositories import conn as _conn
        try:
            from routines.logger import logger_routine as _logger_routine
        except ImportError:
            from logger import logger_routine as _logger_routine

        conn = _conn
        settings = _settings
        logger_routine = _logger_routine
        return conn, settings, logger_routine
    except Exception as e:
        print(f"[ERRO] Não foi possível inicializar conexão com o banco: {e}")
        return None, None, None


SNAPSHOT_DIR = os.path.join(os.getcwd(), 'storage', 'etl_snapshots')
PRE_LOAD_SNAPSHOT_FILE = os.path.join(SNAPSHOT_DIR, 'pre_load_snapshot.json')
LATEST_AUDIT_REPORT_FILE = os.path.join(SNAPSHOT_DIR, 'latest_audit_report.json')

# Lista de tabelas centrais a serem auditadas
AUDIT_TARGETS = [
    {
        "key": "researcher",
        "name": "Pesquisadores Cadastrados",
        "category": "Pessoas",
        "query": "SELECT COUNT(*) AS total FROM public.researcher;",
        "critical_drop": True,
    },
    {
        "key": "graduate_program_researcher",
        "name": "Vínculos Docente-Programa",
        "category": "Programas",
        "query": "SELECT COUNT(*) AS total FROM public.graduate_program_researcher;",
        "critical_drop": True,  # Queda de vínculos = anomalia crítica (ex: bug Hop 21/09)
    },
    {
        "key": "graduate_program_student",
        "name": "Vínculos Discente-Programa",
        "category": "Programas",
        "query": "SELECT COUNT(*) AS total FROM public.graduate_program_student;",
        "critical_drop": True,
    },
    {
        "key": "graduate_program",
        "name": "Programas de Pós-Graduação",
        "category": "Programas",
        "query": "SELECT COUNT(*) AS total FROM public.graduate_program;",
        "critical_drop": True,
    },
    {
        "key": "bibliographic_production",
        "name": "Produção Bibliográfica Total",
        "category": "Produção Científica",
        "query": "SELECT COUNT(*) AS total FROM public.bibliographic_production;",
        "critical_drop": True,
    },
    {
        "key": "bibliographic_production_article",
        "name": "Artigos em Periódicos",
        "category": "Produção Científica",
        "query": "SELECT COUNT(*) AS total FROM public.bibliographic_production_article;",
        "critical_drop": True,
    },
    {
        "key": "guidance",
        "name": "Orientações",
        "category": "Orientações",
        "query": "SELECT COUNT(*) AS total FROM public.guidance;",
        "critical_drop": True,
    },
    {
        "key": "patent",
        "name": "Patentes",
        "category": "Produção Técnica",
        "query": "SELECT COUNT(*) AS total FROM public.patent;",
        "critical_drop": True,
    },
    {
        "key": "software",
        "name": "Softwares Registrados",
        "category": "Produção Técnica",
        "query": "SELECT COUNT(*) AS total FROM public.software;",
        "critical_drop": True,
    },
    {
        "key": "brand",
        "name": "Marcas Registradas",
        "category": "Produção Técnica",
        "query": "SELECT COUNT(*) AS total FROM public.brand;",
        "critical_drop": True,
    },
    {
        "key": "research_project",
        "name": "Projetos de Pesquisa",
        "category": "Projetos",
        "query": "SELECT COUNT(*) AS total FROM public.research_project;",
        "critical_drop": True,
    },
    {
        "key": "participation_events",
        "name": "Participações em Eventos",
        "category": "Eventos",
        "query": "SELECT COUNT(*) AS total FROM public.participation_events;",
        "critical_drop": True,
    },
    {
        "key": "event_organization",
        "name": "Organização de Eventos",
        "category": "Eventos",
        "query": "SELECT COUNT(*) AS total FROM public.event_organization;",
        "critical_drop": True,
    },
    {
        "key": "research_report",
        "name": "Relatórios de Pesquisa",
        "category": "Produção Técnica",
        "query": "SELECT COUNT(*) AS total FROM public.research_report;",
        "critical_drop": False,
    },
]


def ensure_snapshot_dir():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)


def collect_current_metrics():
    """Consulta a contagem atual de cada tabela no banco de dados PostgreSQL."""
    db_conn, _, _ = init_db_connection()
    metrics = {}
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if db_conn is None:
        print(f"[{timestamp}] [ERRO] Conexão com o banco indisponível.")
        for target in AUDIT_TARGETS:
            metrics[target["key"]] = -1
        return {"timestamp": timestamp, "metrics": metrics}

    print(f"[{timestamp}] Coletando métricas do banco de dados...")
    for target in AUDIT_TARGETS:
        key = target["key"]
        query = target["query"]
        try:
            res = db_conn.select(query, one=True)
            total = res.get("total", 0) if res else 0
            metrics[key] = int(total)
            print(f"  - {target['name']} ({key}): {total} registros")
        except Exception as e:
            print(f"  [ERRO] Falha ao consultar {key}: {e}")
            metrics[key] = -1

    return {
        "timestamp": timestamp,
        "metrics": metrics,
    }


def save_pre_load_snapshot():
    """Tira o snapshot antes da rotina de carga/ETL iniciar."""
    ensure_snapshot_dir()
    snapshot = collect_current_metrics()
    with open(PRE_LOAD_SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCESSO] Snapshot pré-carga salvo com sucesso em:")
    print(f"  {PRE_LOAD_SNAPSHOT_FILE}")
    try:
        logger_routine("data_quality_snapshot", False, "Snapshot pré-carga registrado com sucesso.")
    except Exception:
        pass
    return snapshot


def load_pre_load_snapshot():
    """Carrega o snapshot pré-carga salvo anteriormente."""
    if not os.path.exists(PRE_LOAD_SNAPSHOT_FILE):
        print(f"[AVISO] Arquivo de snapshot pré-carga não encontrado em {PRE_LOAD_SNAPSHOT_FILE}")
        return None
    try:
        with open(PRE_LOAD_SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERRO] Falha ao ler snapshot pré-carga: {e}")
        return None


def run_audit(simulated_pre_load=None, simulated_post_load=None):
    """
    Executa a auditoria pós-carga:
    1. Coleta estado atual pós-carga
    2. Lê snapshot pré-carga
    3. Analisa variações e aplica regras de não conformidade
    4. Gera relatório e envia e-mail em caso de irregularidade
    """
    ensure_snapshot_dir()

    if simulated_pre_load:
        pre_snapshot = simulated_pre_load
        print("[MODO SIMULACAO] Usando snapshot simulado para teste de anomalia.")
    else:
        pre_snapshot = load_pre_load_snapshot()

    if simulated_post_load:
        post_snapshot = simulated_post_load
    else:
        post_snapshot = collect_current_metrics()

    if not pre_snapshot:
        print("[ERRO] Nao ha snapshot pre-carga para comparar! Execute primeiro com --snapshot.")
        return False

    pre_metrics = pre_snapshot.get("metrics", {})
    post_metrics = post_snapshot.get("metrics", {})
    pre_time = pre_snapshot.get("timestamp", "N/A")
    post_time = post_snapshot.get("timestamp", "N/A")

    audit_rows = []
    anomalies = []

    print("\n================================================================================")
    print("                 RELATÓRIO DE AUDITORIA DE CARGA (ETL)")
    print(f"   Pré-Carga : {pre_time}")
    print(f"   Pós-Carga : {post_time}")
    print("================================================================================")
    print(f"{'Entidade':<32} | {'Antes':>8} | {'Depois':>8} | {'Delta':>8} | {'Var %':>8} | Status")
    print("-" * 80)

    for target in AUDIT_TARGETS:
        key = target["key"]
        name = target["name"]
        critical_drop = target["critical_drop"]

        before = pre_metrics.get(key, 0)
        after = post_metrics.get(key, 0)

        # Se houve erro de query (-1), registra alerta
        if before < 0 or after < 0:
            status = "ERRO_QUERY"
            anomalies.append({
                "key": key,
                "name": name,
                "severity": "ALTA",
                "message": f"Falha de conexão/leitura na tabela {key}.",
                "before": before,
                "after": after,
                "delta": 0,
                "pct": 0.0,
            })
            audit_rows.append({
                "target": target,
                "before": before,
                "after": after,
                "delta": 0,
                "pct": 0.0,
                "status": "ERRO_QUERY",
                "is_anomaly": True,
            })
            continue

        delta = after - before
        pct = ((after - before) / before * 100.0) if before > 0 else (0.0 if after == 0 else 100.0)

        is_anomaly = False
        status_label = "OK"

        # Regra 1: Tabela zerada (perda total ou carga vazia)
        if after == 0 and before > 0:
            is_anomaly = True
            status_label = "TABELA_ZERADA"
            anomalies.append({
                "key": key,
                "name": name,
                "severity": "CRÍTICA",
                "message": f"A tabela {name} ficou com 0 registros (anterior: {before}).",
                "before": before,
                "after": after,
                "delta": delta,
                "pct": -100.0,
            })

        # Regra 2: Queda inesperada em tabela cumulativa/histórica
        elif critical_drop and delta < 0:
            is_anomaly = True
            status_label = f"QUEDA ({delta})"
            anomalies.append({
                "key": key,
                "name": name,
                "severity": "ALTA",
                "message": f"Queda não permitida de {abs(delta)} registros em {name} ({pct:.2f}%).",
                "before": before,
                "after": after,
                "delta": delta,
                "pct": pct,
            })

        # Regra 3: Variação percentual negativa atípica (> 2% de queda mesmo se não for critical_drop)
        elif pct < -2.0:
            is_anomaly = True
            status_label = f"QUEDA_PERCENTUAL ({pct:.1f}%)"
            anomalies.append({
                "key": key,
                "name": name,
                "severity": "MÉDIA",
                "message": f"Redução percentual atípica de {pct:.2f}% em {name}.",
                "before": before,
                "after": after,
                "delta": delta,
                "pct": pct,
            })

        sign = "+" if delta > 0 else ""
        print(f"{name:<32} | {before:>8} | {after:>8} | {sign + str(delta):>8} | {pct:>7.2f}% | {status_label}")

        audit_rows.append({
            "target": target,
            "before": before,
            "after": after,
            "delta": delta,
            "pct": pct,
            "status": status_label,
            "is_anomaly": is_anomaly,
        })

    print("================================================================================")

    has_non_conformity = len(anomalies) > 0

    if has_non_conformity:
        print(f"\n[NAO CONFORMIDADE DETECTADA] Foram encontradas {len(anomalies)} irregularidade(s) na carga:")
        for an in anomalies:
            print(f"   - [{an['severity']}] {an['name']}: {an['message']}")
    else:
        print("\n[CONFORMIDADE CONFIRMADA] Nenhuma irregularidade detectada na carga de dados.")

    # Salva relatório mais recente em JSON
    audit_report = {
        "pre_timestamp": pre_time,
        "post_timestamp": post_time,
        "has_non_conformity": has_non_conformity,
        "total_anomalies": len(anomalies),
        "anomalies": anomalies,
        "details": [
            {
                "key": r["target"]["key"],
                "name": r["target"]["name"],
                "category": r["target"]["category"],
                "before": r["before"],
                "after": r["after"],
                "delta": r["delta"],
                "pct": round(r["pct"], 2),
                "status": r["status"],
                "is_anomaly": r["is_anomaly"],
            }
            for r in audit_rows
        ],
    }

    with open(LATEST_AUDIT_REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2, ensure_ascii=False)

    # Dispara e-mail de alerta se houver não conformidade (ou se ALERT_ON_SUCCESS estiver ativo)
    should_send_email = has_non_conformity or getattr(settings, "ALERT_ON_SUCCESS", False)

    if should_send_email:
        print("\nDisparando notificação por e-mail...")
        send_audit_email(audit_report)
    else:
        print("\nCarga sem anomalias e ALERT_ON_SUCCESS=False. E-mail de rotina omitido.")

    # Registra no log do PostgreSQL
    try:
        log_msg = f"Auditoria concluída. Anomalias: {len(anomalies)}"
        logger_routine("data_quality_audit", has_non_conformity, log_msg)
    except Exception:
        pass

    return not has_non_conformity


def build_email_html(report):
    """Gera o corpo do e-mail em HTML responsivo e bem formatado."""
    has_non_conformity = report["has_non_conformity"]
    anomalies = report["anomalies"]
    details = report["details"]
    pre_time = report["pre_timestamp"]
    post_time = report["post_timestamp"]

    if has_non_conformity:
        badge_bg = "#dc2626"
        badge_text = "🚨 NÃO CONFORMIDADE DETECTADA"
        summary_text = (
            f"Atenção: A rotina de carga de dados (ETL) identificou <strong>{len(anomalies)} anomalia(s)</strong> "
            f"na integridade das tabelas do iaPós / SIMCC. Ação de verificação necessária."
        )
    else:
        badge_bg = "#16a34a"
        badge_text = "✅ CARGA CONCLUÍDA COM SUCESSO"
        summary_text = "A rotina de carga de dados (ETL) foi executada e todas as tabelas atenderam aos critérios de conformidade."

    anomalies_html = ""
    if anomalies:
        anomalies_html = """
        <div style="background-color: #fef2f2; border-left: 4px solid #dc2626; padding: 15px; margin: 20px 0; border-radius: 4px;">
            <h3 style="color: #991b1b; margin-top: 0; font-size: 16px;">Detalhes das Irregularidades:</h3>
            <ul style="margin: 0; padding-left: 20px; color: #7f1d1d; font-size: 14px;">
        """
        for a in anomalies:
            anomalies_html += f"<li><strong>[{a['severity']}] {a['name']}:</strong> {a['message']}</li>"
        anomalies_html += """
            </ul>
        </div>
        """

    rows_html = ""
    for r in details:
        is_bad = r["is_anomaly"]
        row_bg = "#fee2e2" if is_bad else "#ffffff"
        delta_color = "#dc2626" if r["delta"] < 0 else ("#16a34a" if r["delta"] > 0 else "#6b7280")
        sign = "+" if r["delta"] > 0 else ""
        status_badge = (
            f'<span style="background-color: #dc2626; color: #fff; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{r["status"]}</span>'
            if is_bad
            else '<span style="background-color: #e5e7eb; color: #374151; padding: 3px 8px; border-radius: 12px; font-size: 11px;">OK</span>'
        )

        rows_html += f"""
        <tr style="background-color: {row_bg}; border-bottom: 1px solid #e5e7eb;">
            <td style="padding: 10px 12px; font-size: 13px; font-weight: 500; color: #1f2937;">{r['name']}</td>
            <td style="padding: 10px 12px; font-size: 12px; color: #6b7280;">{r['category']}</td>
            <td style="padding: 10px 12px; font-size: 13px; text-align: right; color: #4b5563;">{r['before']:,}</td>
            <td style="padding: 10px 12px; font-size: 13px; text-align: right; font-weight: 600; color: #111827;">{r['after']:,}</td>
            <td style="padding: 10px 12px; font-size: 13px; text-align: right; font-weight: bold; color: {delta_color};">{sign}{r['delta']:,}</td>
            <td style="padding: 10px 12px; font-size: 13px; text-align: right; color: {delta_color};">{r['pct']:+.2f}%</td>
            <td style="padding: 10px 12px; text-align: center;">{status_badge}</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f9fafb; margin: 0; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .header {{ background-color: #1e3a8a; padding: 24px; color: #ffffff; }}
            .content {{ padding: 24px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            th {{ background-color: #f3f4f6; color: #374151; font-size: 12px; text-transform: uppercase; padding: 10px 12px; text-align: left; border-bottom: 2px solid #e5e7eb; }}
            .footer {{ background-color: #f9fafb; padding: 16px 24px; font-size: 12px; color: #6b7280; border-top: 1px solid #e5e7eb; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div style="font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #93c5fd; margin-bottom: 4px;">iaPós / SIMCC • SENAI CIMATEC</div>
                <h1 style="margin: 0; font-size: 20px; font-weight: 700;">Auditoria de Integridade da Carga de Dados</h1>
            </div>
            <div class="content">
                <div style="display: inline-block; background-color: {badge_bg}; color: #ffffff; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; margin-bottom: 15px;">
                    {badge_text}
                </div>
                <p style="color: #374151; font-size: 14px; line-height: 1.5; margin: 0 0 15px 0;">
                    {summary_text}
                </p>

                <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px 16px; margin-bottom: 20px; font-size: 13px; color: #475569;">
                    <strong>Período Auditado:</strong><br>
                    • Pré-Carga: {pre_time}<br>
                    • Pós-Carga: {post_time}
                </div>

                {anomalies_html}

                <h3 style="color: #1f2937; font-size: 15px; margin-bottom: 8px;">Tabela Comparativa Geral:</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Entidade</th>
                            <th>Categoria</th>
                            <th style="text-align: right;">Antes</th>
                            <th style="text-align: right;">Depois</th>
                            <th style="text-align: right;">Delta (Δ)</th>
                            <th style="text-align: right;">Var %</th>
                            <th style="text-align: center;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
            <div class="footer">
                Este e-mail é gerado automaticamente pelo módulo <code>data_quality_monitor.py</code> integrado à rotina ETL do iaPós.<br>
                Centro Universitário SENAI CIMATEC / UNEB.
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_audit_email(report):
    """Envia o e-mail de alerta utilizando smtplib."""
    smtp_host = getattr(settings, "SMTP_HOST", "smtp.gmail.com") or os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(getattr(settings, "SMTP_PORT", 587) or os.environ.get("SMTP_PORT", 587))
    smtp_user = getattr(settings, "SMTP_USER", "") or os.environ.get("SMTP_USER", "")
    smtp_password = getattr(settings, "SMTP_PASSWORD", "") or os.environ.get("SMTP_PASSWORD", "")
    smtp_from = getattr(settings, "SMTP_FROM", "") or os.environ.get("SMTP_FROM", "") or smtp_user

    recipients_raw = getattr(settings, "ALERT_EMAILS", "") or os.environ.get(
        "ALERT_EMAILS", "eric.queiroz@aln.senaicimatec.edu.br,ejorge@uneb.br"
    )
    recipients = [e.strip() for e in recipients_raw.split(",") if e.strip()]

    has_non_conformity = report["has_non_conformity"]
    anomalies_count = report["total_anomalies"]

    if has_non_conformity:
        subject = f"🚨 [ALERTA iaPós] Não Conformidade Detectada na Carga de Dados ({anomalies_count} anomalia(s))"
    else:
        subject = "✅ [iaPós] Relatório de Carga de Dados Concluída com Sucesso"

    html_content = build_email_html(report)

    # Verifica se as credenciais SMTP estão configuradas
    if not smtp_user or not smtp_password:
        print("[AVISO] Credenciais SMTP (SMTP_USER / SMTP_PASSWORD) não preenchidas no .env!")
        print("  O e-mail não pôde ser transmitido externamente.")
        print(f"  Destinatários previstos: {', '.join(recipients)}")
        print(f"  Assunto: {subject.encode('ascii', 'replace').decode('ascii')}")
        print("  -> O relatório HTML completo foi salvo em disco para consulta local.")
        # Salva o HTML localmente para inspeção
        preview_file = os.path.join(SNAPSHOT_DIR, "latest_email_preview.html")
        with open(preview_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"  -> Preview HTML salvo em: {preview_file}")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_from or smtp_user
    msg["To"] = ", ".join(recipients)

    text_part = MIMEText(
        f"Relatório de Auditoria iaPós\n"
        f"Status: {'ALERTA - Não conformidade detectada' if has_non_conformity else 'Sucesso'}\n"
        f"Anomalias: {anomalies_count}\n"
        f"Verifique o e-mail em um cliente com suporte a HTML.",
        "plain",
        "utf-8",
    )
    html_part = MIMEText(html_content, "html", "utf-8")

    msg.attach(text_part)
    msg.attach(html_part)

    try:
        print(f"Conectando ao servidor SMTP {smtp_host}:{smtp_port}...")
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_password)
        server.sendmail(msg["From"], recipients, msg.as_string())
        server.quit()
        print(f"[SUCESSO] E-mail de alerta enviado com sucesso para: {', '.join(recipients)}")
        return True
    except Exception as e:
        print(f"[ERRO] Falha ao enviar e-mail via SMTP: {e}")
        try:
            logger_routine("data_quality_email_error", True, str(e))
        except Exception:
            pass
        return False


def simulate_anomaly():
    """Simula um cenário de anomalia (ex: 75 vínculos docente-programa sumiram) para validação."""
    real_current = collect_current_metrics()
    # Se não houver banco conectado, gera dados simulados realistas
    if real_current["metrics"].get("researcher", -1) == -1:
        print("[MODO OFFLINE] Banco de dados não conectado. Utilizando valores base de referência do iaPós.")
        real_current = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": {
                "researcher": 124,
                "graduate_program_researcher": 124,
                "graduate_program_student": 181,
                "graduate_program": 5,
                "bibliographic_production": 4210,
                "bibliographic_production_article": 1850,
                "guidance": 309,
                "patent": 42,
                "software": 89,
                "brand": 12,
                "research_project": 95,
                "participation_events": 640,
                "event_organization": 88,
                "research_report": 15,
            }
        }

    simulated_pre = json.loads(json.dumps(real_current))

    # Cria uma anomalia simulada no pré-snapshot:
    # finge que antes tinham +75 vínculos de docente e +120 artigos
    simulated_pre["metrics"]["graduate_program_researcher"] = (
        real_current["metrics"].get("graduate_program_researcher", 124) + 75
    )
    simulated_pre["metrics"]["bibliographic_production_article"] = (
        real_current["metrics"].get("bibliographic_production_article", 1850) + 120
    )
    simulated_pre["timestamp"] = (datetime.datetime.now() - datetime.timedelta(hours=2)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    print("\n--- SIMULACAO DE ANOMALIA ATIVADA ---")
    print("Injetando cenario de teste: perda de 75 vinculos e 120 artigos...")
    run_audit(simulated_pre_load=simulated_pre, simulated_post_load=real_current)


def main():
    parser = argparse.ArgumentParser(description="Monitor de Integridade e Auditoria de Carga de Dados (iaPós)")
    parser.add_argument(
        "--snapshot",
        "--pre",
        action="store_true",
        help="Salva snapshot das contagens das tabelas antes da carga de dados",
    )
    parser.add_argument(
        "--audit",
        "--post",
        action="store_true",
        help="Analisa variação pós-carga, detecta não conformidades e alerta por e-mail",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Exibe contagem atual de todas as tabelas monitoradas",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Simula um cenário de não conformidade para testar os alertas e layout de e-mail",
    )
    parser.add_argument(
        "--test-email",
        action="store_true",
        help="Testa conexão SMTP enviando e-mail de teste",
    )

    # Suporte a argumentos posicionais simples (ex: python data_quality_monitor.py pre / post)
    if len(sys.argv) > 1 and sys.argv[1].lower() in ["pre", "snapshot", "--snapshot"]:
        save_pre_load_snapshot()
        return
    elif len(sys.argv) > 1 and sys.argv[1].lower() in ["post", "audit", "--audit"]:
        run_audit()
        return
    elif len(sys.argv) > 1 and sys.argv[1].lower() in ["status", "--status"]:
        collect_current_metrics()
        return
    elif len(sys.argv) > 1 and sys.argv[1].lower() in ["simulate", "--simulate"]:
        simulate_anomaly()
        return

    args = parser.parse_args()

    if args.snapshot:
        save_pre_load_snapshot()
    elif args.audit:
        run_audit()
    elif args.status:
        collect_current_metrics()
    elif args.simulate:
        simulate_anomaly()
    elif args.test_email:
        test_report = {
            "has_non_conformity": True,
            "total_anomalies": 1,
            "pre_timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "post_timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "anomalies": [
                {
                    "name": "Teste de Conexão SMTP",
                    "severity": "INFORMATIVO",
                    "message": "Este é um disparo de teste para validação das credenciais de e-mail.",
                }
            ],
            "details": [],
        }
        send_audit_email(test_report)
    else:
        # Se nenhum argumento for passado, executa auditoria por padrão
        run_audit()


if __name__ == "__main__":
    main()
