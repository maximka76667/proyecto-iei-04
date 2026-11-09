import sqlite3
from iei.database import (process_source, search_entities, get_entity,
                          statistics, load_issues, loads_history)
from iei.sources import load_source


def by_origin(file, fuente, id_origen):
    """id_entidad es autonumérico: localizar la entidad por su id de origen."""
    conn = sqlite3.connect(file)
    try:
        row = conn.execute("SELECT id_entidad FROM entidades WHERE fuente=? AND id_origen=?",
                           (fuente, id_origen)).fetchone()
    finally:
        conn.close()
    return get_entity(row[0], file) if row else None


def test_three_sources_integrate_and_idempotent(tmp_path):
    file = tmp_path / 'db.sqlite'
    for source in ('CV','CAT','CAN'):
        result = process_source(source,load_source(source),file)
        assert result['leidos'] > 100
        assert result['descartados'] == (61 if source == 'CAN' else 0)
    stats = statistics(file)
    assert stats['total']==3211
    assert stats['fuentes']=={'CV':1697,'CAT':765,'CAN':749}
    assert stats['geolocalizadas'] > 1000
    assert stats['geolocalizadas'] <=1697
    assert by_origin(file,'CV','1')['nombre'].startswith('CENTRO')
    assert by_origin(file,'CAT','306')['codigo_postal']=='08172'
    assert by_origin(file,'CAN','ERE1986CA00001')['fuente']=='CAN'
    assert isinstance(by_origin(file,'CV','1')['id_entidad'], int)
    r = process_source('CV',load_source('CV'),file)
    assert r['insertados']==0
    assert r['actualizados']==0
    assert r['sin_cambios']==1697
    assert statistics(file)['total']==3211
    assert loads_history(file)[0]['fuente']=='CV'
    assert load_issues(r['carga_id'],file)['total']==r['incidencias']


def test_duplicates_and_missing_required_fields(tmp_path):
    base=dict(load_source('CAT')[0]); blank=dict(base);blank['n_mero_registre']=''
    out=process_source('CAT',[base,base,blank],tmp_path/'b.sqlite')
    assert out['leidos']==3
    assert out['insertados']==1
    assert out['descartados']==2
    issues=load_issues(out['carga_id'],tmp_path/'b.sqlite')['items']
    assert any(i['codigo']=='duplicado_lote' for i in issues)
    assert any(i['codigo']=='id_obligatorio' for i in issues)


def test_search_text_geo_and_filters(tmp_path):
    file=tmp_path/'db.sqlite'
    process_source('CV',load_source('CV'),file)
    process_source('CAT',load_source('CAT'),file)
    results=search_entities(file,q='montesinos')
    assert results['total']>=1
    cv=search_entities(file,fuente='CV',limit=3)
    assert cv['total']==1697
    assert len(cv['items'])==3
    province=search_entities(file,provincia='Alicante')
    assert province['total']>100
    only_map=search_entities(file,bbox=(-2,37,1,41))
    assert only_map['total']>1000
    assert all(item['longitud'] is not None for item in only_map['items'])
    no_map=search_entities(file,fuente='CAT',bbox=(-180,-90,180,90))
    assert no_map['total']==0


def test_escaping_like_prevents_accidental_wildcards(tmp_path):
    file=tmp_path/'x.sqlite'; process_source('CV',load_source('CV')[:5],file)
    assert search_entities(file,q='___')['total']==0
    assert search_entities(file,q='%')['total']==0


def test_update_changed_record(tmp_path):
    file=tmp_path/'x.sqlite'; sample=dict(load_source('CV')[0])
    a=process_source('CV',[sample],file)
    sample['nombre']='Nueva denominación'
    b=process_source('CV',[sample],file)
    assert a['insertados']==1 and b['actualizados']==1
    updated = by_origin(file,'CV','1')
    assert updated['nombre']=='Nueva denominación'


def test_reload_keeps_autonumeric_id(tmp_path):
    file=tmp_path/'x.sqlite'; sample=dict(load_source('CV')[0])
    process_source('CV',[sample],file)
    first=by_origin(file,'CV','1')['id_entidad']
    sample['nombre']='Otro nombre'
    process_source('CV',[sample],file)
    assert by_origin(file,'CV','1')['id_entidad']==first


def test_read_errors_are_reported_and_counted(tmp_path):
    file=tmp_path/'x.sqlite'
    errors=[{'line': 7, 'reason': 'Se esperaban 21 columnas y hay 3', 'raw': 'a,b,c'}]
    out=process_source('CV',[dict(load_source('CV')[0])],file,read_errors=errors)
    assert out['leidos']==2 and out['insertados']==1 and out['descartados']==1
    issues=load_issues(out['carga_id'],file)['items']
    bad=[i for i in issues if i['codigo']=='fila_ilegible']
    assert len(bad)==1 and bad[0]['fila']==7 and bad[0]['original']=='a,b,c'
