from fastapi.testclient import TestClient

from iei.sources import load_read_errors, load_source

HEADER = ("WKT,id,ni_centro,tipo_centro,nombre,max,entidad,domici,leyenda,cod_ine_mun,provincia,"
          "comarca,municipio,sector,clasificacion,pobtotal,email,telefono,f_resolu,x_25830,y_25830")
GOOD = ('"POINT (698055 4211247)","1","29",CENTROS SOCIALES,"CENTRO ""VIRGEN, DEL PILAR""","0",'
        'AYTO,"PZA.DE LA IGLESIA, 2",Entidad Local,"03903",Alacant/Alicante,Baix Segura,Los Montesinos,'
        'PERSONAS MAYORES,X,"4912",zero@gva.es,"966721087",1995-09-12 00:00:00,"698055","4211247"')


def write_cv(tmp_path, monkeypatch, *lines):
    (tmp_path / "cv.csv").write_text("\n".join((HEADER, *lines)) + "\n", encoding="utf-8")
    monkeypatch.setenv("IEI_SOURCE_DIR", str(tmp_path))


def test_embedded_comma_and_quotes(tmp_path, monkeypatch):
    write_cv(tmp_path, monkeypatch, GOOD)
    rows = load_source("CV")
    assert len(rows) == 1
    assert rows[0]["nombre"] == 'CENTRO "VIRGEN, DEL PILAR"'
    assert rows[0]["max"] == "0"
    assert len(rows[0]) == 21


def test_malformed_row_is_reported_not_dropped(tmp_path, monkeypatch):
    write_cv(tmp_path, monkeypatch, GOOD, "solo,tres,campos", GOOD.replace('"1"', '"2"', 1))
    rows = load_source("CV")
    errors = load_read_errors("CV")
    assert [r["id"] for r in rows] == ["1", "2"]
    assert len(errors) == 1
    assert errors[0]["line"] == 3
    assert "21" in errors[0]["reason"] and "3" in errors[0]["reason"]
    assert errors[0]["raw"] == "solo,tres,campos"


def test_blank_lines_are_ignored(tmp_path, monkeypatch):
    write_cv(tmp_path, monkeypatch, GOOD, "", GOOD.replace('"1"', '"2"', 1))
    assert len(load_source("CV")) == 2
    assert load_read_errors("CV") == ()


def test_wrapper_exposes_read_errors(tmp_path, monkeypatch):
    write_cv(tmp_path, monkeypatch, GOOD, "a,b")
    monkeypatch.setenv("IEI_WRAPPER_SOURCE", "CV")
    from iei.wrapper import app
    client = TestClient(app)
    body = client.get("/read-errors").json()
    assert body["source"] == "CV" and body["total"] == 1 and body["errors"][0]["line"] == 3
    assert client.get("/records").json()["total"] == 1


def test_real_cv_file_has_no_read_errors():
    assert len(load_source("CV")) == 1697
    assert load_read_errors("CV") == ()
