# Lihtne juhend stress-testimiseks Locust tööriistaga

See juhend aitab sul testida veebirakenduse jõudlust, simuleerides paljude kasutajate samaaegset tegevust.

## 1. Paigaldamine

Esmalt pead paigaldama `locust` teegi. Veendu, et oled oma projekti kaustas ja virtuaalkeskkond on aktiveeritud.

Käivita terminalis käsk:
```bash
pip install locust
```

## 2. Testi käivitamine

1.  **Veendu, et sinu Flaski rakendus töötab.**
    Käivita see terminalis:
    ```bash
    python3 app.py
    ```
    (Rakendus töötab pordil 5001, nagu `app.py` failis määratud.)

2.  **Käivita Locust.**
    Ava **uus terminaliaken** samas kaustas ja käivita järgmine käsk:
    ```bash
    locust -f locustfile.py --host http://localhost:5001
    ```
    - `-f locustfile.py` määrab test-skripti faili.
    - `--host http://localhost:5001` määrab testitava rakenduse aadressi.

## 3. Testi seadistamine veebiliideses

1.  **Ava veebibrauser** ja mine aadressile:
    `http://localhost:8089`

2.  Näed Locust'i seadistusakent. Sisesta sinna:
    - **Number of users**: Mitu kasutajat soovid kokku simuleerida (nt `100`).
    - **Spawn rate**: Mitu uut kasutajat sekundis lisandub, kuni koguarv on saavutatud (nt `10`).

3.  **Vajuta "Start swarming"** nupule.

## 4. Tulemuste jälgimine

Nüüd näed reaalajas, kuidas su rakendus koormusele vastu peab.

- **Statistics** vaates näed iga lehe (`/fast`, `/medium`, `/slow`) kohta statistikat: päringute arv sekundis (RPS), keskmine vastamisaeg, ebaõnnestumiste arv jne.
- **Charts** vaates näed samu andmeid graafikutena.
- **Failures** vaates näed vigade logi, kui mõni päring ebaõnnestub.

Testi peatamiseks vajuta veebiliideses "Stop" nuppu või terminalis `Ctrl + C`.
