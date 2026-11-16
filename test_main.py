import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main


STAGE = {
    "nom_etudiant": "Étudiant Démo",
    "entreprise": "Entreprise Exemple",
    "intitule": "Développement API REST",
    "date_debut": "2026-04-01",
    "date_fin": "2026-06-30",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    test_session = sessionmaker(bind=test_engine)

    def override_get_db():
        with test_session() as session:
            yield session

    # Le démarrage et les requêtes utilisent uniquement la base temporaire.
    monkeypatch.setattr(main, "engine", test_engine)
    main.app.dependency_overrides[main.get_db] = override_get_db
    try:
        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        main.app.dependency_overrides.clear()
        test_engine.dispose()


def test_crud(client):
    response = client.get("/stages")
    assert response.status_code == 200
    assert response.json() == []

    response = client.post("/stages", json=STAGE)
    assert response.status_code == 201
    created = response.json()
    assert isinstance(created["id"], int)
    assert created["id"] > 0
    assert created == {**STAGE, "id": created["id"]}
    url = f"/stages/{created['id']}"

    response = client.get(url)
    assert response.status_code == 200
    assert response.json() == created
    assert client.get("/stages").json() == [created]

    updated = {
        "nom_etudiant": "Étudiant Test",
        "entreprise": "Entreprise Fictive",
        "intitule": "Tests de l'API",
        "date_debut": "2026-05-01",
        "date_fin": "2026-07-31",
    }
    response = client.put(url, json=updated)
    assert response.status_code == 200
    assert response.json() == {**updated, "id": created["id"]}
    assert client.get(url).json() == response.json()

    response = client.delete(url)
    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/stages").json() == []
    assert client.get(url).status_code == 404
    assert client.delete(url).status_code == 404


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_stage(client, method):
    kwargs = {"json": STAGE} if method == "put" else {}
    response = client.request(method, "/stages/999", **kwargs)
    assert response.status_code == 404
    assert response.json() == {"detail": "Stage introuvable."}


@pytest.mark.parametrize("field", list(STAGE))
@pytest.mark.parametrize("method", ["post", "put"])
def test_required_fields(client, field, method):
    invalid = {key: value for key, value in STAGE.items() if key != field}
    created = client.post("/stages", json=STAGE).json()
    url = "/stages" if method == "post" else f"/stages/{created['id']}"
    assert client.request(method, url, json=invalid).status_code == 422
    assert client.get("/stages").json() == [created]


@pytest.mark.parametrize(
    "changes",
    [
        {"date_fin": "2026-03-31"},
        {"date_debut": "2026-02-30"},
        {"date_debut": "01/04/2026"},
        {"date_debut": "2026-4-1"},
        {"date_debut": "2026-04-01T00:00:00"},
        {"date_debut": 0},
        {"date_fin": None},
        {"nom_etudiant": "   "},
        {"entreprise": ""},
        {"intitule": 123},
        {"nom_etudiant": None},
        {"id": 42},
        {"champ_inconnu": "valeur"},
    ],
)
@pytest.mark.parametrize("method", ["post", "put"])
def test_invalid_data(client, changes, method):
    created = client.post("/stages", json=STAGE).json()
    url = "/stages" if method == "post" else f"/stages/{created['id']}"
    response = client.request(method, url, json={**STAGE, **changes})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert client.get("/stages").json() == [created]


def test_equal_dates_and_unique_ids(client):
    payload = {**STAGE, "date_fin": STAGE["date_debut"]}
    first = client.post("/stages", json=payload)
    second = client.post("/stages", json=payload)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert first.json()["date_debut"] == first.json()["date_fin"]
    assert client.get("/stages").json() == [first.json(), second.json()]


def test_swagger_and_openapi(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert set(paths) == {"/stages", "/stages/{id}"}
    assert set(paths["/stages"]) == {"get", "post"}
    assert set(paths["/stages/{id}"]) == {"get", "put", "delete"}
