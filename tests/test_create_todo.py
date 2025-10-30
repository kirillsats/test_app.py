import os
import tempfile
import importlib

# Väga lihtne test ülesande lisamise kohta


def test_create_todo():
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

    # 5) Loome kasutaja ja logime sisse
    r = client.post('/api/register', json={'username': 'jaan', 'password': 'parool1'})
    assert r.is_json and r.get_json()['success'] is True
    r = client.post('/api/login', json={'username': 'jaan', 'password': 'parool1'})
    assert r.is_json and r.get_json()['success'] is True

    # 6) Lisame uue ülesande
    payload = {
        'title': 'Osta piim',
        'description': '2L täispiima',
        'priority': 'high',
        'due_date': '2025-12-31',
        'tags': 'Kodu,Pood'
    }
    r = client.post('/api/todos', json=payload)
    assert r.is_json and r.get_json()['success'] is True

    # 7) Kontrollime, et ülesanne on nimekirjas
    r = client.get('/api/todos')
    assert r.is_json and r.get_json()['success'] is True
    items = r.get_json()['todos']
    assert len(items) == 1
    item = items[0]
    assert item['title'] == 'Osta piim'
    assert item['priority'] == 'high'
    assert item['due_date'] == '2025-12-31'
    assert 'Kodu' in (item.get('tags') or '')

