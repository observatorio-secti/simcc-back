from sqlalchemy.orm import registry

legacy_ufmg_registry = registry()


@legacy_ufmg_registry.mapped_as_dataclass
class UfmgDepartament:
    __tablename__ = 'departament'
    __table_args__ = {'schema': 'ufmg'}

    ...


@legacy_ufmg_registry.mapped_as_dataclass
class UfmgResearcher:
    __tablename__ = 'researcher'
    __table_args__ = {'schema': 'ufmg'}

    ...


@legacy_ufmg_registry.mapped_as_dataclass
class UfmgTechnician:
    __tablename__ = 'technician'
    __table_args__ = {'schema': 'ufmg'}

    ...


@legacy_ufmg_registry.mapped_as_dataclass
class UfmgDepartamentTechnician:
    __tablename__ = 'departament_technician'
    __table_args__ = {'schema': 'ufmg'}

    ...


@legacy_ufmg_registry.mapped_as_dataclass
class UfmgDepartamentResearcher:
    __tablename__ = 'departament_researcher'
    __table_args__ = {'schema': 'ufmg'}

    ...


@legacy_ufmg_registry.mapped_as_dataclass
class UfmgResearcherData:
    __tablename__ = 'researcher_data'
    __table_args__ = {'schema': 'ufmg'}

    ...


@legacy_ufmg_registry.mapped_as_dataclass
class UfmgMandate:
    __tablename__ = 'mandate'
    __table_args__ = {'schema': 'ufmg'}

    ...
