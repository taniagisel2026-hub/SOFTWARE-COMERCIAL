"""
SocialSchedulerService — gestor de cola de publicaciones en CONTENIDO_REDES.

Estados del ciclo de vida:
  BORRADOR → PENDIENTE → PUBLICADO
                      ↘ ERROR
"""
from datetime import date, datetime, timedelta
from typing import Optional

from ...database.connection import get_session
from ...database.models import ContenidoRedes
from .content_generator import ArticuloGenerado
from .image_generator import ImageResult


class SocialSchedulerService:

    def programar(
        self,
        articulo: ArticuloGenerado,
        imagenes: list[ImageResult],
        plataforma: str = "TODAS",
        fecha_publicacion: Optional[date] = None,
    ) -> int:
        """
        Almacena el artículo e imágenes en CONTENIDO_REDES.
        Retorna el id_contenido del registro creado.
        """
        if len(imagenes) < 3:
            raise ValueError(f"Se requieren 3 imágenes; recibidas: {len(imagenes)}")

        fecha_pub = fecha_publicacion or date.today()

        with get_session() as session:
            registro = ContenidoRedes(
                tipo_contenido="ARTICULO_DIARIO",
                plataforma_destino=plataforma,
                texto_publicacion=self._seleccionar_copy(articulo, plataforma),
                url_imagen_1=imagenes[0].url_remota or imagenes[0].url_local,
                url_imagen_2=imagenes[1].url_remota or imagenes[1].url_local,
                url_imagen_3=imagenes[2].url_remota or imagenes[2].url_local,
                url_articulo=str(articulo.fecha_generacion),  # referencia por fecha
                tema_sst=articulo.tema.categoria,
                estado_publicacion="PENDIENTE",
                fecha_generacion=articulo.fecha_generacion,
                fecha_publicacion=fecha_pub,
                generado_por_ia=articulo.modelo_usado,
            )
            session.add(registro)
            session.flush()  # para obtener el id antes del commit
            id_contenido = registro.id_contenido

        return id_contenido

    def programar_semana(
        self,
        articulos: list[ArticuloGenerado],
        imagenes_por_articulo: list[list[ImageResult]],
        plataforma: str = "TODAS",
        fecha_inicio: Optional[date] = None,
    ) -> list[int]:
        """
        Programa una semana completa de contenido (hasta 7 artículos).
        Distribuye automáticamente a días laborales a partir de fecha_inicio.
        """
        inicio = fecha_inicio or date.today()
        ids = []
        dia_actual = inicio
        for articulo, imagenes in zip(articulos, imagenes_por_articulo):
            # Saltar fines de semana para distribución natural
            while dia_actual.weekday() >= 5:
                dia_actual += timedelta(days=1)
            ids.append(self.programar(articulo, imagenes, plataforma, dia_actual))
            dia_actual += timedelta(days=1)
        return ids

    def marcar_publicado(self, id_contenido: int) -> None:
        with get_session() as session:
            registro = session.get(ContenidoRedes, id_contenido)
            if registro is None:
                raise ValueError(f"Contenido id={id_contenido} no encontrado.")
            registro.estado_publicacion = "PUBLICADO"
            registro.fecha_publicacion = date.today()

    def marcar_error(self, id_contenido: int, detalle: str = "") -> None:
        with get_session() as session:
            registro = session.get(ContenidoRedes, id_contenido)
            if registro is None:
                raise ValueError(f"Contenido id={id_contenido} no encontrado.")
            registro.estado_publicacion = "ERROR"
            if detalle:
                registro.texto_publicacion = (
                    f"[ERROR: {detalle[:200]}]\n\n" + (registro.texto_publicacion or "")
                )

    def listar_pendientes(self, plataforma: Optional[str] = None) -> list[ContenidoRedes]:
        with get_session() as session:
            q = session.query(ContenidoRedes).filter(
                ContenidoRedes.estado_publicacion == "PENDIENTE"
            )
            if plataforma:
                q = q.filter(ContenidoRedes.plataforma_destino == plataforma)
            # Retornar copias desligadas de la sesión
            return [self._detach(r) for r in q.order_by(ContenidoRedes.fecha_publicacion).all()]

    def listar_por_fecha(self, fecha: Optional[date] = None) -> list[ContenidoRedes]:
        target = fecha or date.today()
        with get_session() as session:
            registros = (
                session.query(ContenidoRedes)
                .filter(ContenidoRedes.fecha_publicacion == target)
                .order_by(ContenidoRedes.plataforma_destino)
                .all()
            )
            return [self._detach(r) for r in registros]

    def resumen_estadisticas(self) -> dict:
        with get_session() as session:
            total = session.query(ContenidoRedes).count()
            pendientes = session.query(ContenidoRedes).filter_by(estado_publicacion="PENDIENTE").count()
            publicados = session.query(ContenidoRedes).filter_by(estado_publicacion="PUBLICADO").count()
            errores = session.query(ContenidoRedes).filter_by(estado_publicacion="ERROR").count()
        return {
            "total": total,
            "pendientes": pendientes,
            "publicados": publicados,
            "errores": errores,
            "tasa_exito": f"{(publicados / total * 100):.1f}%" if total > 0 else "N/A",
        }

    @staticmethod
    def _seleccionar_copy(articulo: ArticuloGenerado, plataforma: str) -> str:
        mapa = {
            "LINKEDIN":   articulo.copy_linkedin,
            "FACEBOOK":   articulo.copy_facebook,
            "INSTAGRAM":  articulo.copy_instagram,
        }
        texto_base = mapa.get(plataforma, articulo.copy_linkedin)
        hashtags_str = " ".join(articulo.hashtags)
        cta = articulo.cta
        return f"{texto_base}\n\n{hashtags_str}\n\n{cta}"

    @staticmethod
    def _detach(registro: ContenidoRedes) -> ContenidoRedes:
        """Expunge del session para retornar objeto usable fuera del contexto."""
        from sqlalchemy.orm import make_transient
        from sqlalchemy import inspect as sa_inspect
        # Solo detach si está en estado persistent
        if sa_inspect(registro).persistent:
            registro_copy = registro
            return registro_copy
        return registro
