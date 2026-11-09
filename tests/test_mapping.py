from iei.mapping import clean, convert_utm, map_row
from iei.sources import load_source


def test_correct_source_dataset_counts_and_identifiers():
    assert len(load_source('CV')) == 1697
    assert len(load_source('CAT')) == 765
    assert len(load_source('CAN')) == 810
    assert 'denominacion' in load_source('CAN')[0]
    assert 'n_mero_registre' in load_source('CAT')[0]


def test_empty_marker_only_when_field_is_unknown():
    assert clean('_U') is None
    assert clean('  ') is None
    assert clean('Calle _U Uno') == 'Calle _U Uno'
    assert clean('  hola   mundo  ') == 'hola mundo'


def test_cv_mapping_and_coordinate_conversion():
    out = map_row('CV', load_source('CV')[0])
    assert out.accepted
    assert 'id_entidad' not in out.entity  # autonumérico, lo asigna el almacén
    assert out.entity['id_origen'] == '1'
    assert out.locality['codigo'] == '03903'
    assert out.province['codigo'] == '03'
    assert out.entity['ambito'] == 'INCLUSION_SOCIAL'
    assert -1.5 <= out.entity['longitud'] <= 1.5
    assert 37 <= out.entity['latitud'] <= 41
    assert out.entity['codigo_postal'] is None


def test_coordinate_wkt_recovery():
    raw = dict(load_source('CV')[0]); raw['x_25830'] = ''; raw['y_25830'] = ''
    out = map_row('CV', raw)
    assert out.entity['longitud'] is not None
    assert any(x.code == 'ejes_restaurados_wkt' for x in out.issues)


def test_coordinate_malformed_pair_is_null():
    raw = dict(load_source('CV')[0]); raw['x_25830']='invalid';raw['WKT']='junk'
    out = map_row('CV',raw)
    assert out.entity['longitud'] is None
    assert out.entity['latitud'] is None
    assert any(x.code=='coordenadas_invalidas' for x in out.issues)


def test_coordinate_converter_rejects_out_of_bounds():
    try:
        convert_utm(0, 0)
    except ValueError:
        pass
    else:
        assert False, 'Se debía rechazar el eje UTM fuera de rango'


def test_cat_semantics_postal_and_no_geo():
    out = map_row('CAT', load_source('CAT')[0])
    assert out.entity['id_origen'] == '306'
    assert out.entity['ambito'] is None
    assert out.entity['codigo_postal'] == '08172'
    assert out.province == {'codigo':'08','nombre':'Barcelona'}
    assert out.entity['longitud'] is None
    assert out.entity['url'] is None  # no se reconstruye dominio de aspecto incorrecto


def test_can_semantics_and_invalid_website():
    out = map_row('CAN',load_source('CAN')[0])
    assert out.entity['id_origen'] == 'ERE1986CA00001'
    assert out.entity['ambito'] == 'DISCAPACIDAD'
    assert out.entity['url'] is None  # 'wwwadepsi.org' no se repara arbitrariamente
    assert out.entity['longitud'] is None
    assert out.locality['codigo'] == '35001'
    assert out.province['codigo'] == '35'


def test_can_semantic_proposals_are_not_invented():
    row = dict(load_source('CAN')[0]);row['area_nombre']='Drogodependencia'
    out = map_row('CAN',row)
    assert out.entity['ambito'] is None
    assert any(x.code=='ambito_provisional' for x in out.issues)


def test_can_varios_migration_not_forced_without_catalog_confirmation():
    row = dict(load_source('CAN')[0]);row['area_nombre']='Varios';row['subarea_nombre']='Migración'
    out = map_row('CAN',row)
    assert out.entity['ambito'] is None
    assert any(x.code=='migracion_provisional' for x in out.issues)


def test_missing_id_discards_record():
    row = dict(load_source('CAT')[0]);row['n_mero_registre']=''
    out = map_row('CAT',row)
    assert not out.accepted
    assert any(i.code=='id_obligatorio' for i in out.issues)


def test_can_duplicate_phone_repaired():
    row = dict(load_source('CAN')[0]);row['telefono_2']=row['telefono_1']
    out = map_row('CAN',row)
    assert out.entity['contacto'].count('Tel.') == 1
    assert any(i.code=='contacto_duplicado' for i in out.issues)


def test_invalid_postal_is_null_and_record_remains():
    row=dict(load_source('CAT')[0]);row['codi_postal']='foo'
    out=map_row('CAT',row)
    assert out.accepted
    assert out.entity['codigo_postal'] is None
    assert any(i.code=='postal_invalido' for i in out.issues)
