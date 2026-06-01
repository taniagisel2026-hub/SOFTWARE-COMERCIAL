"""
Servicio de cumplimiento Ley 1581 de 2012 (Habeas Data).
Todo módulo de comunicación DEBE invocar verificar_opt_out() antes de enviar.
"""
from datetime import date

from ...database.connection import get_session
from ...database.models import EmpresaProspecto


class HabeasDataError(Exception):
    """Se lanza cuando el envío está bloqueado por opt-out activo."""
    pass


class HabeasDataService:

    def verificar_opt_out(self, id_empresa: int) -> None:
        """Lanza HabeasDataError si la empresa solicitó exclusión."""
        with get_session() as session:
            empresa = session.get(EmpresaProspecto, id_empresa)
            if empresa is None:
                raise ValueError(f"Empresa id={id_empresa} no encontrada en la base de datos.")
            if empresa.opt_out:
                raise HabeasDataError(
                    f"[Ley 1581] Comunicación bloqueada para '{empresa.razon_social}' "
                    f"(opt-out registrado el {empresa.fecha_opt_out}). "
                    f"Motivo: {empresa.motivo_opt_out or 'no especificado'}."
                )

    def registrar_opt_out(
        self,
        id_empresa: int,
        motivo: str = "Solicitud del titular de los datos",
    ) -> None:
        """Marca la empresa como opt-out y bloquea futuras comunicaciones."""
        with get_session() as session:
            empresa = session.get(EmpresaProspecto, id_empresa)
            if empresa is None:
                raise ValueError(f"Empresa id={id_empresa} no encontrada.")
            empresa.opt_out = True
            empresa.fecha_opt_out = date.today()
            empresa.motivo_opt_out = motivo[:300]
            empresa.fecha_ultima_actualizacion = date.today()
        print(f"[Ley 1581] Opt-out registrado para empresa id={id_empresa}.")

    def registrar_opt_in(self, id_empresa: int) -> None:
        """Reactiva comunicaciones si el titular lo autoriza expresamente."""
        with get_session() as session:
            empresa = session.get(EmpresaProspecto, id_empresa)
            if empresa is None:
                raise ValueError(f"Empresa id={id_empresa} no encontrada.")
            empresa.opt_out = False
            empresa.fecha_opt_out = None
            empresa.motivo_opt_out = None
            empresa.fecha_ultima_actualizacion = date.today()
        print(f"[Ley 1581] Opt-in registrado para empresa id={id_empresa}.")
