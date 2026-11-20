import secrets

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
def api_key(monkeypatch):
    key = secrets.token_urlsafe(32)
    monkeypatch.setenv("API_KEY", key)
    return key


@pytest.fixture
def client(tmp_path, monkeypatch, api_key):
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
        with TestClient(main.app, headers={"X-API-Key": api_key}) as test_client:
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
    client.headers.pop("X-API-Key")
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text
    response = client.get("/openapi.json")
    assert response.status_code == 200
    specification = response.json()
    paths = specification["paths"]
    assert set(paths) == {"/stages", "/stages/{id}"}
    assert set(paths["/stages"]) == {"get", "post"}
    assert set(paths["/stages/{id}"]) == {"get", "put", "delete"}
    scheme = specification["components"]["securitySchemes"]["ApiKeyAuth"]
    assert scheme["type"] == "apiKey"
    assert scheme["in"] == "header"
    assert scheme["name"] == "X-API-Key"
    for operations in paths.values():
        for operation in operations.values():
            assert operation["security"] == [{"ApiKeyAuth": []}]
            assert "401" in operation["responses"]


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/stages"),
        ("get", "/stages/{id}"),
        ("post", "/stages"),
        ("put", "/stages/{id}"),
        ("delete", "/stages/{id}"),
    ],
)
@pytest.mark.parametrize("supplied_key", [None, "", "cle-incorrecte", "é"])
def test_all_routes_require_authentication(client, api_key, method, path, supplied_key):
    created = client.post("/stages", json=STAGE).json()
    client.headers.pop("X-API-Key")
    headers = (
        [] if supplied_key is None
        else [(b"X-API-Key", supplied_key.encode("utf-8"))]
    )
    kwargs = {"json": STAGE} if method in {"post", "put"} else {}

    response = client.request(
        method, path.format(id=created["id"]), headers=headers, **kwargs
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Clé API absente ou invalide."}
    assert response.headers["WWW-Authenticate"] == "APIKey"
    assert response.headers["Cache-Control"] == "no-store"
    assert api_key not in response.text
    # Un accès refusé ne doit ni lire les données ni les modifier.
    response = client.get("/stages", headers={"X-API-Key": api_key})
    assert response.status_code == 200
    assert response.json() == [created]


@pytest.mark.parametrize("valid_first", [True, False])
def test_duplicate_key_headers_are_rejected(client, api_key, valid_first):
    client.headers.pop("X-API-Key")
    keys = [api_key, "cle-incorrecte"] if valid_first else ["cle-incorrecte", api_key]
    response = client.get("/stages", headers=[("X-API-Key", key) for key in keys])
    assert response.status_code == 401


def test_query_parameter_does_not_authenticate(client, api_key):
    client.headers.pop("X-API-Key")
    response = client.get("/stages", params={"api_key": api_key, "X-API-Key": api_key})
    assert response.status_code == 401
    assert api_key not in response.text


@pytest.mark.parametrize(
    "path, code",
    [("/stages", 200), ("/stages/999", 404), ("/stages/invalide", 422), ("/docs", 200)],
)
def test_security_headers(client, path, code):
    response = client.get(path)
    assert response.status_code == code
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"


@pytest.mark.parametrize(
    "key", [None, "", "court", "a" * 31, "a" * 129, "é" * 32, "a" * 32 + " "]
)
def test_invalid_configuration_prevents_startup(monkeypatch, key):
    if key is None:
        monkeypatch.delenv("API_KEY", raising=False)
    else:
        monkeypatch.setenv("API_KEY", key)

    def unexpected_database_access(**kwargs):
        pytest.fail("Une configuration invalide ne doit pas ouvrir la base.")

    monkeypatch.setattr(main.Base.metadata, "create_all", unexpected_database_access)
    with pytest.raises(RuntimeError, match="Configurez API_KEY"):
        with TestClient(main.app):
            pass
