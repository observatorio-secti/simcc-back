"""
Módulo de Auditoria de Integridade e Variação dos Dados (ETL Data Quality Monitor)
iaPós / SIMCC - SENAI CIMATEC

Analisa a variação dos dados gerais antes e depois da carga de dados (ETL).
O FATOR PRINCIPAL de detecção de não conformidades é o Índice de Produção (IndProd),
avaliando quedas drásticas nos pesquisadores, nos programas de pós-graduação e no consolidado.
Também audita a integridade estrutural das tabelas de banco (vínculos, contagens, tabelas zeradas).

Quando detecta qualquer não conformidade, gera relatório detalhado e dispara e-mail de alerta.

Uso:
  python routines/data_quality_monitor.py --snapshot   (ou 'pre'  : salva snapshot pré-carga com IndProd e tabelas)
  python routines/data_quality_monitor.py --audit      (ou 'post' : compara pós-carga, detecta variações de IndProd e alerta)
  python routines/data_quality_monitor.py --status     (exibe contagem atual e resumo do IndProd)
  python routines/data_quality_monitor.py --test-email (testa envio SMTP)
  python routines/data_quality_monitor.py --simulate   (simula anomalia de IndProd para homologação do e-mail)
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

# Lista de tabelas estruturais auditadas
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
        "critical_drop": True,
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


def collect_indprod_data(db_conn):
    """
    Coleta o IndProd consolidado por pesquisador, por programa de pós-graduação
    e o total global institucional.
    Avalia os quadriênios 2025-2028 (atual em andamento) e 2021-2024 (referência).
    """
    if db_conn is None:
        return {"global": {}, "programs": [], "researchers": {}}

    try:
        # 1. Coleta IndProd por pesquisador
        SCRIPT_RESEARCHERS = """
        WITH scores AS (
            SELECT
                r.id::text AS researcher_id,
                r.name,
                COALESCE(
                    (
                        SELECT gp.acronym
                        FROM graduate_program_researcher gpr
                        JOIN graduate_program gp ON gp.graduate_program_id = gpr.graduate_program_id
                        WHERE gpr.researcher_id = r.id
                        ORDER BY gp.acronym
                        LIMIT 1
                    ), 'SEM_PROGRAMA'
                ) AS program_acronym,
                COALESCE((
                    SELECT
                        CASE WHEN COUNT(*) = 0 THEN 0.0 ELSE
                        (
                            COALESCE(SUM(ind_prod_article), 0)
                            + COALESCE(SUM(ind_prod_book), 0)
                            + COALESCE(SUM(ind_prod_book_chapter), 0)
                            + COALESCE(SUM(ind_prod_software), 0)
                            + COALESCE(SUM(ind_prod_report), 0)
                            + COALESCE(SUM(ind_prod_granted_patent), 0)
                            + COALESCE(SUM(ind_prod_not_granted_patent), 0)
                        ) / COUNT(*) END
                    FROM researcher_ind_prod rip
                    WHERE rip.researcher_id = r.id
                      AND rip.year >= 2025 AND rip.year <= 2028
                ), 0.0) AS ind_prod_current,
                COALESCE((
                    SELECT
                        CASE WHEN COUNT(*) = 0 THEN 0.0 ELSE
                        (
                            COALESCE(SUM(ind_prod_article), 0)
                            + COALESCE(SUM(ind_prod_book), 0)
                            + COALESCE(SUM(ind_prod_book_chapter), 0)
                            + COALESCE(SUM(ind_prod_software), 0)
                            + COALESCE(SUM(ind_prod_report), 0)
                            + COALESCE(SUM(ind_prod_granted_patent), 0)
                            + COALESCE(SUM(ind_prod_not_granted_patent), 0)
                        ) / COUNT(*) END
                    FROM researcher_ind_prod rip
                    WHERE rip.researcher_id = r.id
                      AND rip.year >= 2021 AND rip.year <= 2024
                ), 0.0) AS ind_prod_previous
            FROM researcher r
        )
        SELECT * FROM scores ORDER BY name;
        """
        rows = db_conn.select(SCRIPT_RESEARCHERS) or []
        researchers = {}
        for r in rows:
            rid = str(r["researcher_id"])
            researchers[rid] = {
                "researcher_id": rid,
                "name": r.get("name") or "Sem Nome",
                "program_acronym": r.get("program_acronym") or "SEM_PROGRAMA",
                "current": round(float(r.get("ind_prod_current", 0) or 0), 2),
                "previous": round(float(r.get("ind_prod_previous", 0) or 0), 2),
            }

        # 2. Coleta IndProd por Programa
        SCRIPT_PROGRAMS = """
        SELECT
            gp.graduate_program_id::text,
            gp.name,
            gp.acronym,
            COALESCE(SUM(
                CASE WHEN gpip.year >= 2025 AND gpip.year <= 2028 THEN
                    COALESCE(ind_prod_article, 0)
                    + COALESCE(ind_prod_book, 0)
                    + COALESCE(ind_prod_book_chapter, 0)
                    + COALESCE(ind_prod_software, 0)
                    + COALESCE(ind_prod_report, 0)
                    + COALESCE(ind_prod_granted_patent, 0)
                    + COALESCE(ind_prod_not_granted_patent, 0)
                ELSE 0 END
            ), 0.0) AS ind_prod_current,
            COALESCE(SUM(
                CASE WHEN gpip.year >= 2021 AND gpip.year <= 2024 THEN
                    COALESCE(ind_prod_article, 0)
                    + COALESCE(ind_prod_book, 0)
                    + COALESCE(ind_prod_book_chapter, 0)
                    + COALESCE(ind_prod_software, 0)
                    + COALESCE(ind_prod_report, 0)
                    + COALESCE(ind_prod_granted_patent, 0)
                    + COALESCE(ind_prod_not_granted_patent, 0)
                ELSE 0 END
            ), 0.0) AS ind_prod_previous
        FROM graduate_program gp
        LEFT JOIN graduate_program_ind_prod gpip ON gpip.graduate_program_id = gp.graduate_program_id
        GROUP BY gp.graduate_program_id, gp.name, gp.acronym
        ORDER BY gp.acronym;
        """
        prog_rows = db_conn.select(SCRIPT_PROGRAMS) or []
        programs = []
        for p in prog_rows:
            programs.append({
                "graduate_program_id": str(p["graduate_program_id"]),
                "name": p.get("name") or "",
                "acronym": p.get("acronym") or "PROG",
                "current": round(float(p.get("ind_prod_current", 0) or 0), 2),
                "previous": round(float(p.get("ind_prod_previous", 0) or 0), 2),
            })

        # 3. Métricas Globais
        current_values = [r["current"] for r in researchers.values() if r["current"] > 0]
        total_sum = round(sum(current_values), 2)
        total_avg = round(total_sum / len(current_values), 2) if current_values else 0.0

        global_metrics = {
            "total_researchers": len(researchers),
            "researchers_with_indprod": len(current_values),
            "ind_prod_sum": total_sum,
            "ind_prod_avg": total_avg,
        }

        return {
            "global": global_metrics,
            "programs": programs,
            "researchers": researchers,
        }
    except Exception as e:
        print(f"  [ERRO] Falha ao coletar métricas de IndProd: {e}")
        return {"global": {}, "programs": [], "researchers": {}}


def collect_current_metrics():
    """Consulta a contagem atual das tabelas e as métricas de IndProd no PostgreSQL."""
    db_conn, _, _ = init_db_connection()
    metrics = {}
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if db_conn is None:
        print(f"[{timestamp}] [ERRO] Conexão com o banco indisponível.")
        for target in AUDIT_TARGETS:
            metrics[target["key"]] = -1
        return {"timestamp": timestamp, "metrics": metrics, "indprod": {}}

    print(f"[{timestamp}] Coletando contagens das tabelas do banco...")
    for target in AUDIT_TARGETS:
        key = target["key"]
        query = target["query"]
        try:
            res = db_conn.select(query, one=True)
            total = res.get("total", 0) if res else 0
            metrics[key] = int(total)
        except Exception as e:
            print(f"  [ERRO] Falha ao consultar {key}: {e}")
            metrics[key] = -1

    print(f"[{timestamp}] Coletando métricas do Índice de Produção (IndProd)...")
    indprod_data = collect_indprod_data(db_conn)
    glob = indprod_data.get("global", {})
    print(f"  - Total Pesquisadores: {glob.get('total_researchers', 0)} ({glob.get('researchers_with_indprod', 0)} ativos)")
    print(f"  - IndProd Médio Global (2025-2028): {glob.get('ind_prod_avg', 0):.2f}")
    print(f"  - IndProd Somado Global: {glob.get('ind_prod_sum', 0):.2f}")

    return {
        "timestamp": timestamp,
        "metrics": metrics,
        "indprod": indprod_data,
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


def audit_indprod(pre_indprod, post_indprod):
    """
    Avalia a variação de IndProd entre pré-carga e pós-carga:
    - Quedas em docentes individuais (zerados ou queda >= 10%);
    - Quedas por programa de pós-graduação;
    - Variação global institucional.
    """
    anomalies = []
    researcher_changes = []
    program_changes = []

    pre_researchers = pre_indprod.get("researchers", {}) if pre_indprod else {}
    post_researchers = post_indprod.get("researchers", {}) if post_indprod else {}

    # 1. Auditoria individual por pesquisador
    for rid, pre_info in pre_researchers.items():
        name = pre_info.get("name", "Docente")
        prog = pre_info.get("program_acronym", "—")
        before = pre_info.get("current", 0.0)

        post_info = post_researchers.get(rid)
        after = post_info.get("current", 0.0) if post_info else 0.0

        delta = round(after - before, 2)
        pct = round(((after - before) / before * 100.0), 2) if before > 0 else (0.0 if after == 0 else 100.0)

        is_anomaly = False
        severity = "NORMAL"
        msg = ""

        # Regra A: Docente que tinha pontuação e ZEROU totalmente
        if before >= 1.0 and after == 0.0:
            is_anomaly = True
            severity = "CRÍTICA"
            msg = f"Docente {name} ({prog}) teve seu IndProd zerado pós-ETL: {before:.2f} -> 0.00 (-100%)."
        # Regra B: Queda drástica (> 15% e perda de pelo menos 0.5 pontos)
        elif delta <= -0.5 and pct <= -15.0:
            is_anomaly = True
            severity = "ALTA"
            msg = f"Queda drástica de {abs(pct):.1f}% no IndProd de {name} ({prog}): {before:.2f} -> {after:.2f} (Δ {delta:+.2f})."
        # Regra C: Queda moderada/atípica (10% a 15% e delta <= -0.3)
        elif delta <= -0.3 and pct <= -10.0:
            is_anomaly = True
            severity = "MÉDIA"
            msg = f"Redução no IndProd de {name} ({prog}): {before:.2f} -> {after:.2f} (queda de {abs(pct):.1f}%)."

        if is_anomaly:
            anomalies.append({
                "type": "INDPROD_RESEARCHER",
                "key": rid,
                "name": name,
                "program": prog,
                "severity": severity,
                "message": msg,
                "before": before,
                "after": after,
                "delta": delta,
                "pct": pct,
            })

        if delta != 0.0:
            researcher_changes.append({
                "researcher_id": rid,
                "name": name,
                "program": prog,
                "before": before,
                "after": after,
                "delta": delta,
                "pct": pct,
                "is_anomaly": is_anomaly,
                "severity": severity,
            })

    # Ordena pesquisadores pelas maiores quedas (piores deltas primeiro)
    researcher_changes.sort(key=lambda x: x["delta"])

    # 2. Auditoria por programa
    pre_programs = {p["acronym"]: p for p in (pre_indprod.get("programs", []) if pre_indprod else [])}
    post_programs = {p["acronym"]: p for p in (post_indprod.get("programs", []) if post_indprod else [])}

    for acronym, pre_prog in pre_programs.items():
        name = pre_prog.get("name", acronym)
        before = pre_prog.get("current", 0.0)
        post_prog = post_programs.get(acronym)
        after = post_prog.get("current", 0.0) if post_prog else 0.0

        delta = round(after - before, 2)
        pct = round(((after - before) / before * 100.0), 2) if before > 0 else (0.0 if after == 0 else 100.0)

        is_anomaly = False
        if before > 0 and (delta < -1.0 or pct < -5.0):
            is_anomaly = True
            anomalies.append({
                "type": "INDPROD_PROGRAM",
                "key": acronym,
                "name": f"Programa {acronym}",
                "program": acronym,
                "severity": "ALTA",
                "message": f"O programa {acronym} sofreu redução de {abs(pct):.1f}% no IndProd total: {before:.2f} -> {after:.2f} (Δ {delta:+.2f}).",
                "before": before,
                "after": after,
                "delta": delta,
                "pct": pct,
            })

        program_changes.append({
            "acronym": acronym,
            "name": name,
            "before": before,
            "after": after,
            "delta": delta,
            "pct": pct,
            "is_anomaly": is_anomaly,
        })

    # 3. Auditoria global
    pre_global = pre_indprod.get("global", {}) if pre_indprod else {}
    post_global = post_indprod.get("global", {}) if post_indprod else {}
    glob_before_sum = pre_global.get("ind_prod_sum", 0.0)
    glob_after_sum = post_global.get("ind_prod_sum", 0.0)
    glob_delta = round(glob_after_sum - glob_before_sum, 2)
    glob_pct = round(((glob_after_sum - glob_before_sum) / glob_before_sum * 100.0), 2) if glob_before_sum > 0 else 0.0

    if glob_before_sum > 0 and glob_pct < -5.0:
        anomalies.append({
            "type": "INDPROD_GLOBAL",
            "key": "GLOBAL",
            "name": "IndProd Global Institucional",
            "program": "TODOS",
            "severity": "CRÍTICA",
            "message": f"Queda geral de {abs(glob_pct):.1f}% no IndProd institucional somado: {glob_before_sum:.2f} -> {glob_after_sum:.2f} (Δ {glob_delta:+.2f}).",
            "before": glob_before_sum,
            "after": glob_after_sum,
            "delta": glob_delta,
            "pct": glob_pct,
        })

    return {
        "anomalies": anomalies,
        "researcher_changes": researcher_changes,
        "program_changes": program_changes,
        "global_summary": {
            "before_sum": glob_before_sum,
            "after_sum": glob_after_sum,
            "delta_sum": glob_delta,
            "pct_sum": glob_pct,
            "before_avg": pre_global.get("ind_prod_avg", 0.0),
            "after_avg": post_global.get("ind_prod_avg", 0.0),
            "total_researchers": post_global.get("total_researchers", 0),
        }
    }


def run_audit(simulated_pre_load=None, simulated_post_load=None):
    """
    Executa a auditoria pós-carga:
    1. Coleta estado atual pós-carga
    2. Lê snapshot pré-carga
    3. Analisa variações de IndProd e contagens de tabelas
    4. Gera relatório consolidado e dispara e-mail caso haja não conformidade
    """
    ensure_snapshot_dir()

    if simulated_pre_load:
        pre_snapshot = simulated_pre_load
        print("[MODO SIMULAÇÃO] Usando snapshot simulado para teste de anomalia de IndProd.")
    else:
        pre_snapshot = load_pre_load_snapshot()

    if simulated_post_load:
        post_snapshot = simulated_post_load
    else:
        post_snapshot = collect_current_metrics()

    if not pre_snapshot:
        print("[ERRO] Não há snapshot pré-carga para comparar! Execute primeiro com --snapshot.")
        return False

    pre_metrics = pre_snapshot.get("metrics", {})
    post_metrics = post_snapshot.get("metrics", {})
    pre_indprod = pre_snapshot.get("indprod", {})
    post_indprod = post_snapshot.get("indprod", {})
    pre_time = pre_snapshot.get("timestamp", "N/A")
    post_time = post_snapshot.get("timestamp", "N/A")

    audit_rows = []
    anomalies = []

    # 1. Auditoria Estrutural das Tabelas
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

        if before < 0 or after < 0:
            status = "ERRO_QUERY"
            anomalies.append({
                "type": "TABLE_STRUCTURE",
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

        if after == 0 and before > 0:
            is_anomaly = True
            status_label = "TABELA_ZERADA"
            anomalies.append({
                "type": "TABLE_STRUCTURE",
                "key": key,
                "name": name,
                "severity": "CRÍTICA",
                "message": f"A tabela {name} ficou com 0 registros (anterior: {before}).",
                "before": before,
                "after": after,
                "delta": delta,
                "pct": -100.0,
            })
        elif critical_drop and delta < 0:
            is_anomaly = True
            status_label = f"QUEDA ({delta})"
            anomalies.append({
                "type": "TABLE_STRUCTURE",
                "key": key,
                "name": name,
                "severity": "ALTA",
                "message": f"Queda não permitida de {abs(delta)} registros em {name} ({pct:.2f}%).",
                "before": before,
                "after": after,
                "delta": delta,
                "pct": pct,
            })
        elif pct < -2.0:
            is_anomaly = True
            status_label = f"QUEDA_PERCENTUAL ({pct:.1f}%)"
            anomalies.append({
                "type": "TABLE_STRUCTURE",
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

    # 2. Auditoria Especializada de Índice de Produção (IndProd)
    print("\n--------------------------------------------------------------------------------")
    print("           AUDITORIA DE ÍNDICE DE PRODUÇÃO (IndProd 2025–2028)")
    print("--------------------------------------------------------------------------------")

    indprod_audit = audit_indprod(pre_indprod, post_indprod)
    indprod_anomalies = indprod_audit["anomalies"]
    anomalies.extend(indprod_anomalies)

    glob = indprod_audit["global_summary"]
    sign_glob = "+" if glob["delta_sum"] > 0 else ""
    print(f"IndProd Global (Soma) : {glob['before_sum']:.2f} -> {glob['after_sum']:.2f} ({sign_glob}{glob['delta_sum']:.2f} | {glob['pct_sum']:+.2f}%)")
    print(f"IndProd Global (Média): {glob['before_avg']:.2f} -> {glob['after_avg']:.2f}")

    if indprod_audit["program_changes"]:
        print("\nVariação por Programa de Pós-Graduação:")
        for p in indprod_audit["program_changes"]:
            sign_p = "+" if p["delta"] > 0 else ""
            status_p = "🚨 ALERTA" if p["is_anomaly"] else "OK"
            print(f"  - {p['acronym']:<8}: {p['before']:>7.2f} -> {p['after']:>7.2f} ({sign_p}{p['delta']:>6.2f} | {p['pct']:>+6.1f}%) [{status_p}]")

    if indprod_anomalies:
        print(f"\n[MUDANÇA DRÁSTICA DE INDPROD] {len(indprod_anomalies)} anomalia(s) de IndProd detectada(s):")
        for an in indprod_anomalies:
            print(f"   - [{an['severity']}] {an['name']}: {an['message']}")
    else:
        print("\n[INDPROD EM CONFORMIDADE] Nenhuma queda drástica no Índice de Produção.")

    print("================================================================================")

    has_non_conformity = len(anomalies) > 0

    if has_non_conformity:
        print(f"\n[NÃO CONFORMIDADE TOTAL] Foram detectadas {len(anomalies)} irregularidade(s) no total pós-ETL.")
    else:
        print("\n[CONFORMIDADE CONFIRMADA] Carga de dados concluída sem anomalias.")

    audit_report = {
        "pre_timestamp": pre_time,
        "post_timestamp": post_time,
        "has_non_conformity": has_non_conformity,
        "total_anomalies": len(anomalies),
        "anomalies": anomalies,
        "indprod_audit": indprod_audit,
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

    should_send_email = has_non_conformity or getattr(settings, "ALERT_ON_SUCCESS", False)

    if should_send_email:
        print("\nDisparando e-mail de alerta de auditoria do ETL...")
        send_audit_email(audit_report)
    else:
        print("\nCarga sem anomalias e ALERT_ON_SUCCESS=False. E-mail de rotina omitido.")

    try:
        log_msg = f"Auditoria concluída. Anomalias: {len(anomalies)} (IndProd: {len(indprod_anomalies)})"
        logger_routine("data_quality_audit", has_non_conformity, log_msg)
    except Exception:
        pass

    return not has_non_conformity


def build_email_html(report):
    """Gera o corpo do e-mail em HTML responsivo com foco nas variações de IndProd."""
    has_non_conformity = report["has_non_conformity"]
    anomalies = report["anomalies"]
    details = report["details"]
    pre_time = report["pre_timestamp"]
    post_time = report["post_timestamp"]
    indprod_audit = report.get("indprod_audit", {})
    glob = indprod_audit.get("global_summary", {})
    researcher_changes = indprod_audit.get("researcher_changes", [])
    program_changes = indprod_audit.get("program_changes", [])

    indprod_anomalies_count = len([a for a in anomalies if "INDPROD" in a.get("type", "")])

    if has_non_conformity:
        badge_bg = "#dc2626"
        badge_text = "🚨 NÃO CONFORMIDADE DETECTADA NO ETL"
        summary_text = (
            f"A rotina de carga de dados identificou <strong>{len(anomalies)} anomalia(s)</strong>, "
            f"sendo <strong>{indprod_anomalies_count} relacionadas ao Índice de Produção (IndProd)</strong>. "
            f"Recomenda-se verificação imediata dos registros de pesquisadores no Lattes/Hop."
        )
    else:
        badge_bg = "#16a34a"
        badge_text = "✅ CARGA CONCLUÍDA EM CONFORMIDADE"
        summary_text = "A rotina de carga de dados foi executada com sucesso. Os índices de produção e tabelas estruturais atenderam aos critérios de conformidade."

    # Bloco de Anomalias em Destaque
    anomalies_html = ""
    if anomalies:
        anomalies_html = """
        <div style="background-color: #fef2f2; border-left: 4px solid #dc2626; padding: 16px; margin: 20px 0; border-radius: 4px;">
            <h3 style="color: #991b1b; margin-top: 0; font-size: 15px; text-transform: uppercase; letter-spacing: 0.5px;">Resumo das Irregularidades Detectadas:</h3>
            <ul style="margin: 0; padding-left: 20px; color: #7f1d1d; font-size: 13.5px; line-height: 1.5;">
        """
        for a in anomalies:
            anomalies_html += f"<li><strong>[{a.get('severity', 'ALTA')}] {a.get('name', '')}:</strong> {a.get('message', '')}</li>"
        anomalies_html += """
            </ul>
        </div>
        """

    # Tabela de Docentes com Variações Críticas de IndProd
    top_indprod_drops = [r for r in researcher_changes if r.get("is_anomaly") or r.get("delta", 0) <= -0.5]
    docentes_indprod_html = ""
    if top_indprod_drops:
        rows_docentes = ""
        for d in top_indprod_drops[:15]:
            delta_color = "#dc2626" if d["delta"] < 0 else "#16a34a"
            sev_badge = (
                '<span style="background-color: #dc2626; color: #fff; padding: 2px 7px; border-radius: 10px; font-size: 10.5px; font-weight: bold;">CRÍTICA</span>'
                if d.get("severity") == "CRÍTICA"
                else '<span style="background-color: #f97316; color: #fff; padding: 2px 7px; border-radius: 10px; font-size: 10.5px; font-weight: bold;">ALTA</span>'
            )
            rows_docentes += f"""
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 8px 10px; font-size: 12.5px; font-weight: 600; color: #111827;">{d['name']}</td>
                <td style="padding: 8px 10px; font-size: 12px; color: #6b7280; text-align: center;">{d['program']}</td>
                <td style="padding: 8px 10px; font-size: 12.5px; text-align: right; color: #4b5563;">{d['before']:.2f}</td>
                <td style="padding: 8px 10px; font-size: 12.5px; text-align: right; font-weight: 700; color: #111827;">{d['after']:.2f}</td>
                <td style="padding: 8px 10px; font-size: 12.5px; text-align: right; font-weight: 800; color: {delta_color};">{d['delta']:+.2f}</td>
                <td style="padding: 8px 10px; font-size: 12.5px; text-align: right; font-weight: 700; color: {delta_color};">{d['pct']:+.1f}%</td>
                <td style="padding: 8px 10px; text-align: center;">{sev_badge}</td>
            </tr>
            """
        docentes_indprod_html = f"""
        <div style="margin: 24px 0;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <h3 style="color: #1e3a8a; font-size: 14.5px; font-weight: 800; text-transform: uppercase; margin: 0;">
                    🎯 Docentes com Queda Drástica no IndProd (2025–2028)
                </h3>
                <span style="font-size: 11.5px; color: #dc2626; font-weight: bold;">{len(top_indprod_drops)} afetado(s)</span>
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                <thead>
                    <tr style="background-color: #f1f5f9; border-bottom: 2px solid #cbd5e1;">
                        <th style="padding: 8px 10px; text-align: left; color: #475569;">Docente</th>
                        <th style="padding: 8px 10px; text-align: center; color: #475569;">Programa</th>
                        <th style="padding: 8px 10px; text-align: right; color: #475569;">IndProd Pré</th>
                        <th style="padding: 8px 10px; text-align: right; color: #475569;">IndProd Pós</th>
                        <th style="padding: 8px 10px; text-align: right; color: #475569;">Variação (Δ)</th>
                        <th style="padding: 8px 10px; text-align: right; color: #475569;">Var %</th>
                        <th style="padding: 8px 10px; text-align: center; color: #475569;">Severidade</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_docentes}
                </tbody>
            </table>
        </div>
        """

    # Tabela de Programas
    programas_html = ""
    if program_changes:
        prog_rows = ""
        for p in program_changes:
            delta_color = "#dc2626" if p["delta"] < 0 else ("#16a34a" if p["delta"] > 0 else "#6b7280")
            status_badge = (
                '<span style="background-color: #dc2626; color: #fff; padding: 2px 7px; border-radius: 10px; font-size: 10.5px; font-weight: bold;">QUEDA</span>'
                if p["is_anomaly"]
                else '<span style="background-color: #e2e8f0; color: #475569; padding: 2px 7px; border-radius: 10px; font-size: 10.5px;">ESTÁVEL</span>'
            )
            prog_rows += f"""
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 8px 10px; font-weight: bold; color: #1e3a8a;">{p['acronym']}</td>
                <td style="padding: 8px 10px; color: #4b5563;">{p['name']}</td>
                <td style="padding: 8px 10px; text-align: right; color: #4b5563;">{p['before']:.2f}</td>
                <td style="padding: 8px 10px; text-align: right; font-weight: 700; color: #111827;">{p['after']:.2f}</td>
                <td style="padding: 8px 10px; text-align: right; font-weight: 800; color: {delta_color};">{p['delta']:+.2f}</td>
                <td style="padding: 8px 10px; text-align: right; font-weight: 700; color: {delta_color};">{p['pct']:+.1f}%</td>
                <td style="padding: 8px 10px; text-align: center;">{status_badge}</td>
            </tr>
            """
        programas_html = f"""
        <div style="margin: 20px 0;">
            <h3 style="color: #1e3a8a; font-size: 14px; font-weight: 800; text-transform: uppercase; margin: 0 0 8px 0;">
                📊 Variação do IndProd por Programa de Pós-Graduação
            </h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                <thead>
                    <tr style="background-color: #f1f5f9; border-bottom: 2px solid #cbd5e1;">
                        <th style="padding: 8px 10px; text-align: left; color: #475569;">Sigla</th>
                        <th style="padding: 8px 10px; text-align: left; color: #475569;">Programa</th>
                        <th style="padding: 8px 10px; text-align: right; color: #475569;">Pré-Carga</th>
                        <th style="padding: 8px 10px; text-align: right; color: #475569;">Pós-Carga</th>
                        <th style="padding: 8px 10px; text-align: right; color: #475569;">Δ</th>
                        <th style="padding: 8px 10px; text-align: right; color: #475569;">Var %</th>
                        <th style="padding: 8px 10px; text-align: center; color: #475569;">Status</th>
                    </tr>
                </thead>
                <tbody>
                    {prog_rows}
                </tbody>
            </table>
        </div>
        """

    # Tabela Estrutural Geral das Tabelas
    rows_html = ""
    for r in details:
        is_bad = r["is_anomaly"]
        row_bg = "#fee2e2" if is_bad else "#ffffff"
        delta_color = "#dc2626" if r["delta"] < 0 else ("#16a34a" if r["delta"] > 0 else "#6b7280")
        sign = "+" if r["delta"] > 0 else ""
        status_badge = (
            f'<span style="background-color: #dc2626; color: #fff; padding: 2px 7px; border-radius: 10px; font-size: 10.5px; font-weight: bold;">{r["status"]}</span>'
            if is_bad
            else '<span style="background-color: #e5e7eb; color: #374151; padding: 2px 7px; border-radius: 10px; font-size: 10.5px;">OK</span>'
        )

        rows_html += f"""
        <tr style="background-color: {row_bg}; border-bottom: 1px solid #e5e7eb;">
            <td style="padding: 8px 10px; font-size: 12.5px; font-weight: 500; color: #1f2937;">{r['name']}</td>
            <td style="padding: 8px 10px; font-size: 11.5px; color: #6b7280;">{r['category']}</td>
            <td style="padding: 8px 10px; font-size: 12.5px; text-align: right; color: #4b5563;">{r['before']:,}</td>
            <td style="padding: 8px 10px; font-size: 12.5px; text-align: right; font-weight: 600; color: #111827;">{r['after']:,}</td>
            <td style="padding: 8px 10px; font-size: 12.5px; text-align: right; font-weight: bold; color: {delta_color};">{sign}{r['delta']:,}</td>
            <td style="padding: 8px 10px; font-size: 12.5px; text-align: right; color: {delta_color};">{r['pct']:+.2f}%</td>
            <td style="padding: 8px 10px; text-align: center;">{status_badge}</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 18px; }}
            .container {{ max-width: 820px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.06); }}
            .header {{ background-color: #1e3a8a; padding: 22px 28px; color: #ffffff; }}
            .content {{ padding: 24px 28px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ background-color: #f1f5f9; color: #334155; font-size: 11.5px; text-transform: uppercase; padding: 8px 10px; text-align: left; }}
            .footer {{ background-color: #f8fafc; padding: 16px 28px; font-size: 11.5px; color: #64748b; border-top: 1px solid #e2e8f0; }}
            .kpi-box {{ background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 12px 16px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1.2px; color: #93c5fd; margin-bottom: 4px; font-weight: 700;">iaPós / SIMCC • SENAI CIMATEC</div>
                <h1 style="margin: 0; font-size: 19px; font-weight: 800;">Auditoria de Integridade e Variação de IndProd (ETL)</h1>
            </div>
            <div class="content">
                <div style="display: inline-block; background-color: {badge_bg}; color: #ffffff; padding: 6px 14px; border-radius: 16px; font-size: 11.5px; font-weight: 800; margin-bottom: 14px;">
                    {badge_text}
                </div>
                <p style="color: #334155; font-size: 13.5px; line-height: 1.5; margin: 0 0 16px 0;">
                    {summary_text}
                </p>

                <!-- Cards de Resumo Executivo do IndProd -->
                <div style="display: table; width: 100%; margin-bottom: 20px;">
                    <div style="display: table-row;">
                        <div style="display: table-cell; width: 33%; padding-right: 8px;">
                            <div class="kpi-box">
                                <div style="font-size: 11px; color: #1e3a8a; font-weight: 700; text-transform: uppercase;">IndProd Global (Soma)</div>
                                <div style="font-size: 18px; font-weight: 800; color: #1e3a8a; margin: 4px 0;">{glob.get('after_sum', 0):.2f}</div>
                                <div style="font-size: 11px; color: #64748b;">Antes: {glob.get('before_sum', 0):.2f} ({glob.get('pct_sum', 0):+.1f}%)</div>
                            </div>
                        </div>
                        <div style="display: table-cell; width: 33%; padding: 0 4px;">
                            <div class="kpi-box">
                                <div style="font-size: 11px; color: #1e3a8a; font-weight: 700; text-transform: uppercase;">IndProd Médio Docente</div>
                                <div style="font-size: 18px; font-weight: 800; color: #1e3a8a; margin: 4px 0;">{glob.get('after_avg', 0):.2f}</div>
                                <div style="font-size: 11px; color: #64748b;">Antes: {glob.get('before_avg', 0):.2f}</div>
                            </div>
                        </div>
                        <div style="display: table-cell; width: 33%; padding-left: 8px;">
                            <div style="background: {'#fef2f2' if indprod_anomalies_count > 0 else '#f0fdf4'}; border: 1px solid {'#fecaca' if indprod_anomalies_count > 0 else '#bbf7d0'}; border-radius: 6px; padding: 12px 16px; text-align: center;">
                                <div style="font-size: 11px; color: {'#991b1b' if indprod_anomalies_count > 0 else '#166534'}; font-weight: 700; text-transform: uppercase;">Quedas Drásticas</div>
                                <div style="font-size: 18px; font-weight: 800; color: {'#dc2626' if indprod_anomalies_count > 0 else '#16a34a'}; margin: 4px 0;">{indprod_anomalies_count}</div>
                                <div style="font-size: 11px; color: #64748b;">Docentes com queda relevante</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 14px; margin-bottom: 18px; font-size: 12px; color: #475569;">
                    <strong>Período Auditado:</strong> Pré-Carga: {pre_time} &nbsp;·&nbsp; Pós-Carga: {post_time}
                </div>

                {anomalies_html}
                {docentes_indprod_html}
                {programas_html}

                <h3 style="color: #1e3a8a; font-size: 14px; font-weight: 800; text-transform: uppercase; margin: 24px 0 8px 0;">
                    📋 Integridade Estrutural das Tabelas do Sistema
                </h3>
                <table>
                    <thead>
                        <tr style="border-bottom: 2px solid #cbd5e1;">
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
    indprod_anomalies = [a for a in report.get("anomalies", []) if "INDPROD" in a.get("type", "")]

    if has_non_conformity:
        if indprod_anomalies:
            subject = f"🚨 [ALERTA iaPós] Queda Drástica de IndProd Detectada no ETL ({len(indprod_anomalies)} docente(s) afetado(s))"
        else:
            subject = f"🚨 [ALERTA iaPós] Não Conformidade Estrutural no ETL ({anomalies_count} anomalia(s))"
    else:
        subject = "✅ [iaPós] Carga de Dados Concluída com Sucesso (IndProd em Conformidade)"

    html_content = build_email_html(report)

    # Sempre salva uma cópia local do preview HTML para auditoria e conferência
    preview_file = os.path.join(SNAPSHOT_DIR, "latest_email_preview.html")
    os.makedirs(os.path.dirname(preview_file), exist_ok=True)
    with open(preview_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  -> Preview HTML do e-mail salvo em: {preview_file}")

    if not smtp_user or not smtp_password:
        print("[AVISO] Credenciais SMTP (SMTP_USER / SMTP_PASSWORD) não preenchidas no .env!")
        print("  O e-mail não pôde ser transmitido externamente via rede.")
        print(f"  Destinatários previstos: {', '.join(recipients)}")
        print(f"  Assunto: {subject.encode('ascii', 'replace').decode('ascii')}")
        print("  -> O relatório HTML completo está disponível no arquivo preview salvo acima.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_from or smtp_user
    msg["To"] = ", ".join(recipients)

    text_part = MIMEText(
        f"Relatório de Auditoria iaPós\n"
        f"Status: {'ALERTA - Não conformidade detectada' if has_non_conformity else 'Sucesso'}\n"
        f"Anomalias no IndProd: {len(indprod_anomalies)}\n"
        f"Anomalias Totais: {anomalies_count}\n"
        f"Verifique o relatório completo no cliente de e-mail com suporte a HTML.",
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
    """
    Simula um cenário realista de não conformidade pós-ETL:
    - 3 docentes sofrem quedas drásticas no IndProd (um é zerado totalmente e dois sofrem perda severa);
    - Um programa de pós-graduação sofre queda no IndProd total;
    - Perda de vínculos docente-programa.
    """
    print("\n--- SIMULAÇÃO DE ANOMALIA DE INDPROD ATIVADA ---")
    real_current = collect_current_metrics()

    # Se estiver offline sem banco, cria base simulada realista
    if real_current["metrics"].get("researcher", -1) == -1 or not real_current.get("indprod", {}).get("researchers"):
        print("[MODO OFFLINE] Utilizando dados base de referência do iaPós.")
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
            },
            "indprod": {
                "global": {
                    "total_researchers": 124,
                    "researchers_with_indprod": 98,
                    "ind_prod_sum": 412.50,
                    "ind_prod_avg": 4.21,
                },
                "programs": [
                    {"graduate_program_id": "1", "name": "GESTÃO E TECNOLOGIA INDUSTRIAL", "acronym": "GETEC", "current": 142.30, "previous": 280.10},
                    {"graduate_program_id": "2", "name": "MODELAGEM COMPUTACIONAL", "acronym": "MCTI", "current": 128.50, "previous": 250.40},
                    {"graduate_program_id": "3", "name": "ENGENHARIA MECÂNICA", "acronym": "PEIR", "current": 89.20, "previous": 190.00},
                    {"graduate_program_id": "4", "name": "DESENVOLVIMENTO SUSTENTÁVEL", "acronym": "MPDS", "current": 52.50, "previous": 110.20},
                ],
                "researchers": {
                    "r1": {"researcher_id": "r1", "name": "Fernando Luiz Pellegrini Pessoa", "program_acronym": "GETEC", "current": 3.50, "previous": 7.94},
                    "r2": {"researcher_id": "r2", "name": "Alex Álisson Bandeira Santos", "program_acronym": "MCTI", "current": 5.80, "previous": 8.10},
                    "r3": {"researcher_id": "r3", "name": "Herman Lepikson", "program_acronym": "GETEC", "current": 4.60, "previous": 6.50},
                    "r4": {"researcher_id": "r4", "name": "Valter Estevão Beal", "program_acronym": "PEIR", "current": 6.20, "previous": 9.30},
                    "r5": {"researcher_id": "r5", "name": "Ingrid Winkler", "program_acronym": "MCTI", "current": 4.10, "previous": 5.80},
                }
            }
        }

    simulated_pre = json.loads(json.dumps(real_current))
    simulated_post = json.loads(json.dumps(real_current))

    # Injeta anomalia drástica no pós-carga:
    res_list = list(simulated_post["indprod"]["researchers"].values())
    if len(res_list) >= 3:
        # Prioriza docentes com IndProd > 0 para simular a queda
        with_score = [r for r in res_list if r.get("current", 0) > 0]
        chosen = with_score[:3] if len(with_score) >= 3 else res_list[:3]

        # 1. Primeiro docente tem seu IndProd zerado (bug de extração do Lattes)
        r1_id = chosen[0]["researcher_id"]
        simulated_pre["indprod"]["researchers"][r1_id]["current"] = 5.20
        simulated_post["indprod"]["researchers"][r1_id]["current"] = 0.00

        # 2. Segundo docente sofre queda drástica de 6.80 para 1.50 (-78%)
        r2_id = chosen[1]["researcher_id"]
        simulated_pre["indprod"]["researchers"][r2_id]["current"] = 6.80
        simulated_post["indprod"]["researchers"][r2_id]["current"] = 1.50

        # 3. Terceiro docente sofre queda de 4.80 para 2.20 (-54%)
        r3_id = chosen[2]["researcher_id"]
        simulated_pre["indprod"]["researchers"][r3_id]["current"] = 4.80
        simulated_post["indprod"]["researchers"][r3_id]["current"] = 2.20
    else:
        for rid, name, prog, pre_v, post_v in [
            ("r1", "Fernando Luiz Pellegrini Pessoa", "GETEC", 5.20, 0.00),
            ("r2", "Alex Álisson Bandeira Santos", "MCTI", 6.80, 1.50),
            ("r3", "Herman Lepikson", "GETEC", 4.80, 2.20),
        ]:
            simulated_pre["indprod"]["researchers"][rid] = {"researcher_id": rid, "name": name, "program_acronym": prog, "current": pre_v, "previous": pre_v}
            simulated_post["indprod"]["researchers"][rid] = {"researcher_id": rid, "name": name, "program_acronym": prog, "current": post_v, "previous": pre_v}

    # 4. Programa GETEC com queda drástica
    for p in simulated_pre["indprod"]["programs"]:
        if p["acronym"] == "GETEC":
            p["current"] = 165.00
    for p in simulated_post["indprod"]["programs"]:
        if p["acronym"] == "GETEC":
            p["current"] = 120.00

    # 5. Queda de 18 vínculos de docente no programa
    simulated_pre["metrics"]["graduate_program_researcher"] = (
        real_current["metrics"].get("graduate_program_researcher", 124) + 18
    )

    simulated_pre["timestamp"] = (datetime.datetime.now() - datetime.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")

    print("Injetando cenário de não conformidade no IndProd:")
    print("  - Docente com IndProd zerado pós-ETL (5.20 -> 0.00)");
    print("  - 2 Docentes com queda drástica > 50% de IndProd");
    print("  - Programa GETEC com queda acentuada");
    print("  - Queda de 18 vínculos docente-programa");

    run_audit(simulated_pre_load=simulated_pre, simulated_post_load=simulated_post)


def main():
    parser = argparse.ArgumentParser(description="Monitor de Integridade e Auditoria de IndProd e ETL (iaPós)")
    parser.add_argument(
        "--snapshot",
        "--pre",
        action="store_true",
        help="Salva snapshot das contagens das tabelas e do IndProd antes da carga",
    )
    parser.add_argument(
        "--audit",
        "--post",
        action="store_true",
        help="Analisa variação de IndProd e tabelas pós-carga, detecta não conformidades e alerta por e-mail",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Exibe estado atual de tabelas e métricas de IndProd",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Simula anomalias drásticas no IndProd para homologar detecção e layout do e-mail",
    )
    parser.add_argument(
        "--test-email",
        action="store_true",
        help="Testa conexão SMTP enviando e-mail de teste",
    )

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
                    "message": "Este é um disparo de teste para validação das credenciais de e-mail e servidor SMTP.",
                }
            ],
            "details": [],
            "indprod_audit": {
                "anomalies": [],
                "researcher_changes": [],
                "program_changes": [],
                "global_summary": {
                    "before_sum": 380.0,
                    "after_sum": 380.0,
                    "delta_sum": 0.0,
                    "pct_sum": 0.0,
                    "before_avg": 4.2,
                    "after_avg": 4.2,
                }
            }
        }
        send_audit_email(test_report)
    else:
        run_audit()


if __name__ == "__main__":
    main()
