import os
import tempfile
import importlib


def setup_test_app():
    """Loob ajutise andmebaasi ja initsialiseerib rakenduse"""
    db = tempfile.NamedTemporaryFile(delete=False)
    db_path = db.name
    db.close()
    os.environ["DB_PATH"] = db_path

    app_module = importlib.import_module("app")
    importlib.reload(app_module)
    app = app_module.app
    app_module.init_db()
    app.testing = True
    client = app.test_client()
    return client, app_module


def test_register_and_login():
    """Kasutaja registreerimine ja sisselogimine"""
    client, _ = setup_test_app()

    # Registreerime uue kasutaja
    r = client.post("/api/register", json={"username": "toomas", "password": "salasona"})
    assert r.status_code == 200
    assert r.get_json()["success"] is True

    # Logime sisse
    a = client.post("/api/login", json={"username": "toomas", "password": "salasona"})
    assert a.get_json()["success"] is True

    # Vale sisselogimine
    b = client.post("/api/login", json={"username": "vale", "password": "vale"})
    assert b.get_json()["success"] is False


def test_password_change():
    """Parooli muutmine (Parooli muutmine)"""
    client, _ = setup_test_app()

    # Lood uue kasutaja
    client.post("/api/register", json={"username": "anna", "password": "123456"})
    client.post("/api/login", json={"username": "anna", "password": "123456"})

    # Muudame parooli
    resp = client.post("/api/change-password", json={
        "old_password": "123456",
        "new_password": "654321"
    })
    data = resp.get_json()
    assert data["success"] is True
    assert "Parool muudetud" in data["message"]

    # Kontrollime, et vana parool enam ei tööta
    client.post("/api/logout")
    r1 = client.post("/api/login", json={"username": "anna", "password": "123456"})
    assert r1.get_json()["success"] is False

    # Kontrollime, et uus parool töötab
    r2 = client.post("/api/login", json={"username": "anna", "password": "654321"})
    assert r2.get_json()["success"] is True


def test_todo_add():
    """To-Do listi lisamine"""
    client, app_module = setup_test_app()

    # Registreerime ja logime sisse
    client.post("/api/register", json={"username": "mart", "password": "qwerty"})
    client.post("/api/login", json={"username": "mart", "password": "qwerty"})

    # Lisame uue ülesande
    todo_data = {
        "title": "Osta piim",
        "description": "2 liitrit täispiima",
        "priority": "high",
        "due_date": "2025-10-30",
        "tags": "pood,piim"
    }
    resp = client.post("/api/todos", json=todo_data)
    data = resp.get_json()
    assert data["success"] is True

    # Kontrollime, et ülesanne eksisteerib
    todos = client.get("/api/todos").get_json()
    assert todos["success"] is True
    assert len(todos["todos"]) == 1
    assert todos["todos"][0]["title"] == "Osta piim"
    assert todos["todos"][0]["priority"] == "high"


def test_todo_delete():
    """To-Do listi kustutamine"""
    client, app_module = setup_test_app()

    # Loo kasutaja ja logi sisse
    client.post("/api/register", json={"username": "kaarel", "password": "parool"})
    client.post("/api/login", json={"username": "kaarel", "password": "parool"})

    # Lisa üks ülesanne
    resp_add = client.post("/api/todos", json={"title": "Korista tuba"})
    assert resp_add.get_json()["success"] is True

    # Kontrolli olemasolu
    resp_all = client.get("/api/todos").get_json()
    assert len(resp_all["todos"]) == 1
    todo_id = resp_all["todos"][0]["id"]

    # Kustuta ülesanne
    resp_del = client.delete(f"/api/todos/{todo_id}")
    assert resp_del.get_json()["success"] is True

    # Kontrolli, et enam pole
    resp_all2 = client.get("/api/todos").get_json()
    assert len(resp_all2["todos"]) == 0
