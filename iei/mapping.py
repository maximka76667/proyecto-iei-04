"""Transformaciones semánticas auditables de CV/CAT/CAN al esquema integrado.

Basado en Mapping_semantico_entrega.docx.pdf del equipo 4. Las equivalencias
provisionales NO se fuerzan y se documentan como incidencias.
"""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import urlparse
from pyproj import Transformer

_TRANSFORM = Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True)
_WKT = re.compile(r"^POINT\s*\(\s*([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s*\)$", re.I)
_POSTAL = re.compile(r"^\d{5}$")
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_CV_AREAS = {
    "PERSONAS MAYORES": "MAYORES",
    "PERSONAS CON DISCAPACIDAD": "DISCAPACIDAD",
    "PERSONAS CON ENFERMEDAD MENTAL": "SALUD_MENTAL",
    "PERSONAS MIGRANTES": "MIGRACION",
    "INFANCIA": "INFANCIA_Y_JUVENTUD",
    "MUJERES": "MUJER",
    "POBLACIÓN EN GENERAL Y COLECTIVOS SOCIALMENTE DESFAVORECIDOS": "INCLUSION_SOCIAL",
}
_CAN_AREAS = {
    "Tercera Edad": "MAYORES", "Discapacidad": "DISCAPACIDAD",
    "Menores Y Juventud": "INFANCIA_Y_JUVENTUD", "Mujer": "MUJER",
    "Exclusión Social": "INCLUSION_SOCIAL",
}
_AMBITOS_PROPUESTOS = {"Drogodependencia", "Centros Ocupacionales", "Voluntariado"}
_CAT_PROVINCES = {"08": "Barcelona", "17": "Girona", "25": "Lleida", "43": "Tarragona"}


def clean(value) -> str | None:
    """Vacíos reales y marcadores de origen, sin alterar texto legítimo."""
    if value is None:
        return None
    result = " ".join(str(value).split())
    return None if result.casefold() in {"", "_u", "null", "none"} else result


def search_text(value) -> str:
    s = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(c for c in s if not unicodedata.combining(c))


@dataclass
class Issue:
    field: str
    code: str
    severity: str
    message: str
    original: str | None = None
    repaired: str | None = None


@dataclass
class Mapped:
    entity: dict = field(default_factory=dict)
    locality: dict = field(default_factory=dict)
    province: dict = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)
    accepted: bool = True

    def note(self, field: str, code: str, severity: str, message: str,
             original=None, repaired=None):
        self.issues.append(Issue(field, code, severity, message,
                                 str(original) if original is not None else None,
                                 str(repaired) if repaired is not None else None))


def _postal(value, out: Mapped, field_name: str) -> str | None:
    value = clean(value)
    if value and not _POSTAL.fullmatch(value):
        out.note(field_name, "postal_invalido", "error", "Código postal inválido; se deja NULL", value)
        return None
    return value


def _ine(value, out: Mapped, field_name: str, digits: int = 5) -> str | None:
    value = clean(value)
    if value is None:
        return None
    if not value.isascii() or not value.isdigit() or len(value) > digits:
        out.note(field_name, "codigo_ine_invalido", "error", "Código INE inválido; se deja NULL", value)
        return None
    padded = value.zfill(digits)
    if padded != value:
        out.note(field_name, "codigo_ine_reparado", "reparacion", "Ceros iniciales restaurados", value, padded)
    return padded


def _province_code(value, out: Mapped) -> str | None:
    value = clean(value)
    if not value:
        return None
    if not re.fullmatch(r"\d{1,2}", value):
        out.note("provincia_codigo", "codigo_provincia_invalido", "error", "Código de provincia inválido", value)
        return None
    return value.zfill(2)


def _url(value, out: Mapped) -> str | None:
    value = clean(value)
    if not value:
        return None
    candidate = value
    if not urlparse(candidate).scheme:
        # Solo completamos la forma inequívoca www.dominio.tld.
        if candidate.lower().startswith("www."):
            candidate = "https://" + candidate
            out.note("url", "esquema_url_anadido", "reparacion", "Esquema https:// añadido a URL inequívoca", value, candidate)
        else:
            out.note("url", "url_sin_esquema", "advertencia", "No se ha inventado un dominio o esquema para esta URL", value)
            return None
    parsed = urlparse(candidate)
    host = parsed.hostname or ""
    if parsed.scheme not in ("http", "https") or not re.fullmatch(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", host):
        out.note("url", "url_invalida", "error", "URL de origen no válida; se deja NULL", value)
        return None
    return candidate


def _contacts(out: Mapped, candidates: list[tuple[str, object, str]]) -> str | None:
    parts = []
    seen = set()
    for field_name, raw, label in candidates:
        value = clean(raw)
        if not value:
            continue
        if label == "Email" and not _EMAIL.fullmatch(value):
            out.note(field_name, "email_invalido", "error", "Correo mal formado; no se importa", value)
            continue
        if label == "Email":
            value = value.lower()
        dedup = (label, value.casefold())
        if dedup in seen:
            out.note(field_name, "contacto_duplicado", "reparacion", "Contacto repetido omitido", value)
            continue
        seen.add(dedup)
        parts.append(f"{label}: {value}")
    return " | ".join(parts) if parts else None


def convert_utm(x: object, y: object) -> tuple[float, float]:
    """Devuelve (longitud, latitud). Lanza ValueError para ejes inválidos."""
    try:
        xx, yy = float(x), float(y)
    except (TypeError, ValueError) as exc:
        raise ValueError("Coordenadas UTM no numéricas") from exc
    if not all(map(math.isfinite, (xx, yy))) or not 100000 <= xx <= 900000 or not 0 <= yy <= 10000000:
        raise ValueError("Coordenadas UTM fuera de rango")
    lon, lat = _TRANSFORM.transform(xx, yy)
    if not math.isfinite(lon) or not math.isfinite(lat) or not -180 <= lon <= 180 or not -90 <= lat <= 90:
        raise ValueError("La transformación UTM ha producido coordenadas inválidas")
    return round(lon, 7), round(lat, 7)


def _coords_cv(raw: dict, out: Mapped) -> tuple[float | None, float | None]:
    sx, sy = clean(raw.get("x_25830")), clean(raw.get("y_25830"))
    original_wkt = clean(raw.get("WKT"))
    wkt_pair = None
    if original_wkt:
        match = _WKT.fullmatch(original_wkt)
        if match:
            wkt_pair = (match.group(1), match.group(2))
        else:
            out.note("WKT", "wkt_invalido", "error", "WKT POINT inválido", original_wkt)
    if sx is not None and sy is not None and wkt_pair:
        try:
            if abs(float(sx) - float(wkt_pair[0])) > 5 or abs(float(sy) - float(wkt_pair[1])) > 5:
                out.note("WKT", "coordenadas_discordantes", "advertencia",
                         "El WKT y los ejes UTM discrepan; se mantienen los ejes x_25830/y_25830", original_wkt)
        except (ValueError, TypeError):
            pass
    if (sx is None or sy is None) and wkt_pair:
        sx, sy = wkt_pair
        out.note("coordenadas", "ejes_restaurados_wkt", "reparacion", "Se recuperaron ambos ejes del WKT", raw.get("x_25830"), f"{sx},{sy}")
    if sx is None and sy is None:
        return None, None
    if sx is None or sy is None:
        out.note("coordenadas", "coordenadas_incompletas", "error", "Falta un eje; ambas coordenadas quedan NULL", f"{sx},{sy}")
        return None, None
    try:
        lon, lat = convert_utm(sx, sy)
    except ValueError as exc:
        out.note("coordenadas", "coordenadas_invalidas", "error", str(exc), f"{sx},{sy}")
        return None, None
    if not (-2.5 <= lon <= 1.5 and 37 <= lat <= 41):
        out.note("coordenadas", "ubicacion_atipica", "advertencia", "El punto está fuera de la zona geográfica esperada; verificar", f"{lon},{lat}")
    return lon, lat


def _address_can(raw: dict) -> str | None:
    parts = []
    for key in ("direccion_tipo_via", "direccion_nombre_via", "direccion_numero", "direccion_complemento"):
        value = clean(raw.get(key))
        if value:
            if key == "direccion_numero" and parts and value == parts[-1]:
                continue
            parts.append(value)
    return " ".join(parts) if parts else None


def map_row(source: str, raw: dict) -> Mapped:
    """Mapea un registro y devuelve además todas las incidencias recuperables."""
    if not isinstance(raw, dict):
        raise TypeError("El registro fuente debe ser un objeto")
    if source not in {"CV", "CAT", "CAN"}:
        raise ValueError(f"Fuente desconocida: {source}")
    out = Mapped()
    raw_id_field = {"CV": "id", "CAT": "n_mero_registre", "CAN": "numero_registro"}[source]
    name_field = {"CV": "nombre", "CAT": "nom_de_l_entitat", "CAN": "denominacion"}[source]
    raw_id = clean(raw.get(raw_id_field))
    name = clean(raw.get(name_field))
    if not raw_id:
        out.accepted = False
        out.note(raw_id_field, "id_obligatorio", "error", "Registro descartado: no tiene ID de origen")
    if not name:
        out.accepted = False
        out.note(name_field, "nombre_obligatorio", "error", "Registro descartado: no tiene nombre")

    ent = dict(id_entidad=f"{source}-{raw_id}" if raw_id else None, fuente=source,
               id_origen=raw_id, nombre=name, ambito=None, direccion=None,
               codigo_postal=None, longitud=None, latitud=None,
               descripcion=None, contacto=None, url=None)
    loc = {"codigo": None, "nombre": None}
    prov = {"codigo": None, "nombre": None}
    out.entity, out.locality, out.province = ent, loc, prov

    if source == "CV":
        sector = clean(raw.get("sector"))
        ent["ambito"] = _CV_AREAS.get(sector or "")
        if sector and not ent["ambito"]:
            out.note("sector", "ambito_no_mapeado", "advertencia", "Sin equivalencia semántica aprobada", sector)
        ent["direccion"] = clean(raw.get("domici"))
        ent["descripcion"] = clean(raw.get("tipo_centro"))
        ent["contacto"] = _contacts(out, [("telefono", raw.get("telefono"), "Tel."), ("email", raw.get("email"), "Email")])
        ent["longitud"], ent["latitud"] = _coords_cv(raw, out)
        loc["codigo"] = _ine(raw.get("cod_ine_mun"), out, "cod_ine_mun")
        loc["nombre"] = clean(raw.get("municipio"))
        prov["codigo"] = loc["codigo"][:2] if loc["codigo"] else None
        prov["nombre"] = clean(raw.get("provincia"))
        if loc["codigo"] and prov["nombre"]:
            p = search_text(prov["nombre"])
            expected = {"03": ("alicante", "alacant"), "12": ("castellon", "castello"), "46": ("valencia", "valencia")}.get(prov["codigo"])
            if expected and not any(alias in p for alias in expected):
                out.note("provincia", "provincia_ine_inconsistente", "advertencia", "El nombre de provincia no parece corresponder con el INE", prov["nombre"])

    elif source == "CAT":
        ent["direccion"] = clean(raw.get("adre_a"))
        ent["codigo_postal"] = _postal(raw.get("codi_postal"), out, "codi_postal")
        ent["descripcion"] = clean(raw.get("naturalesa"))
        ent["contacto"] = _contacts(out, [("tel_fon", raw.get("tel_fon"), "Tel."), ("tel_fon_m_bil", raw.get("tel_fon_m_bil"), "Tel."), ("correu_electr_nic", raw.get("correu_electr_nic"), "Email")])
        ent["url"] = _url(raw.get("web"), out)
        loc["nombre"] = clean(raw.get("municipi"))
        if ent["codigo_postal"]:
            prefix = ent["codigo_postal"][:2]
            if prefix in _CAT_PROVINCES:
                prov["codigo"] = prefix
                prov["nombre"] = _CAT_PROVINCES[prefix]
            else:
                out.note("codi_postal", "codigo_postal_provincia", "advertencia", "El CP no corresponde a una provincia catalana; provincia NULL", ent["codigo_postal"])

    else:  # CAN
        area, subarea = clean(raw.get("area_nombre")), clean(raw.get("subarea_nombre"))
        ent["ambito"] = _CAN_AREAS.get(area or "")
        if area == "Varios" and subarea == "Migración":
            # El mapping lo señala explícitamente como PROVISIONAL.
            out.note("subarea_nombre", "migracion_provisional", "advertencia", "Correspondencia pendiente de validación del catálogo global", subarea)
        elif area in _AMBITOS_PROPUESTOS or (area and not ent["ambito"]):
            out.note("area_nombre", "ambito_provisional", "advertencia", "Categoría no confirmada en el catálogo global; NULL", area)
        ent["direccion"] = _address_can(raw)
        ent["descripcion"] = subarea
        ent["contacto"] = _contacts(out, [("telefono_1", raw.get("telefono_1"), "Tel."), ("telefono_2", raw.get("telefono_2"), "Tel.")])
        ent["url"] = _url(raw.get("pagina_web"), out)
        loc["codigo"] = _ine(raw.get("direccion_municipio_id"), out, "direccion_municipio_id")
        loc["nombre"] = clean(raw.get("direccion_municipio_nombre"))
        prov["codigo"] = _province_code(raw.get("direccion_provincia_id"), out)
        prov["nombre"] = clean(raw.get("direccion_provincia_nombre"))
        if loc["codigo"] and prov["codigo"] and loc["codigo"][:2] != prov["codigo"]:
            out.note("direccion_provincia_id", "codigos_geograficos_inconsistentes", "advertencia", "Código de municipio y provincia no concuerdan", f"{loc['codigo']} / {prov['codigo']}")

    if not loc["nombre"] and loc["codigo"]:
        out.note("localidad", "localidad_sin_nombre", "advertencia", "Se conserva el INE, pero falta nombre de localidad")
    return out
