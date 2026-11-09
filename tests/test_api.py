import pytest
from fastapi.testclient import TestClient
from iei import api
from iei.sources import load_source
from iei.database import process_source


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('IEI_DB_PATH',str(tmp_path/'db.sqlite'))
    return TestClient(api.app)


def test_api_search_and_geojson(client, tmp_path, monkeypatch):
    process_source('CV',load_source('CV')[:20],tmp_path/'db.sqlite')
    response=client.get('/api/entities?fuente=CV&limit=5')
    assert response.status_code==200
    assert response.json()['total']==20
    assert len(response.json()['items'])==5
    geo=client.get('/api/map?bbox=-2,37,1,41')
    assert geo.status_code==200
    assert geo.json()['type']=='FeatureCollection'
    assert len(geo.json()['features']) >= 1
    assert client.get('/api/metadata').status_code==200
    assert client.get('/docs').status_code==200


def test_api_bounding_box_validation(client):
    for bad in ('1,2,3','1,2,3,4,5','-181,2,3,4','nan,0,1,2','0,90,20,-1'):
        assert client.get('/api/entities',params={'bbox':bad}).status_code==422


def test_coordinate_service(client):
    r=client.post('/api/coordinates/convert',json={'x_25830':698055,'y_25830':4211247})
    assert r.status_code==200
    assert 37<r.json()['latitud']<41
    assert client.post('/api/coordinates/convert',json={'x_25830':0,'y_25830':0}).status_code==422


def test_frontend_and_not_found(client):
    assert client.get('/').status_code==200
    assert 'OpenLayers' in client.get('/').text or 'openlayers' in client.get('/').text.lower()
    assert client.get('/api/entities/CAN-not-found').status_code==404
    assert client.get('/api/loads/999/issues').status_code==404


def test_wrapper_direct(monkeypatch):
    from iei.wrapper import app
    monkeypatch.setenv('IEI_WRAPPER_SOURCE','CAT')
    client=TestClient(app)
    r=client.get('/records?page=1&page_size=10')
    assert r.status_code==200
    assert r.json()['source']=='CAT'
    assert r.json()['total']==765
    assert len(r.json()['records'])==10
    assert 'n_mero_registre' in r.json()['records'][0]
    assert client.get('/schema').json()['count']==765
    assert client.get('/records?page_size=600').status_code==422
