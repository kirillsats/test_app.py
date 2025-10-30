import os
import tempfile
import importlib

# Väga lihtne test sisselogimise kohta


def test_login():
    # 1) Teeme ajutise andmebaasi faili
    db = tempfile.NamedTemporaryFile(delete=False)
    db_path = db.name
    db.close()

    # 2) Määrame rakendusele andmebaasi asukoha
    os.environ['DB_PATH'] = db_path

    # 3) Impordime appi ja loome andmebaasi
    app_module = importlib.import_module('app')
    importlib.reload(app_module)
    app = app_module.app
    app_module.init_db()
    app.testing = True

    # 4) Teeme test kliendi
    client = app.test_client()

    # 5) Registreerime kasutaja
    r = client.post('/api/register', json={'username': 'maria', 'password': 'salasona'})
    assert r.is_json
    assert r.get_json()['success'] is True

    # 6) Vale parooliga sisselogimine
    r = client.post('/api/login', json={'username': 'maria', 'password': 'vale'})
    assert r.is_json
    assert r.get_json()['success'] is False

    # 7) Õige parooliga sisselogimine
    r = client.post('/api/login', json={'username': 'maria', 'password': 'salasona'})
    assert r.is_json
    assert r.get_json()['success'] is True

