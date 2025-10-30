from locust import HttpUser, task, between

# See on lihtne Locust-fail stress-testimiseks.
# See simuleerib kasutajaid, kes külastavad erineva kiirusega lehti.

class WebsiteUser(HttpUser):
    # Iga virtuaalne kasutaja ootab 1 kuni 3 sekundit enne uue tegevuse alustamist.
    wait_time = between(1, 3)

    @task(3) # See tegevus on 3x tõenäolisem kui teised
    def visit_fast_page(self):
        """See funktsioon simuleerib kiire lehe külastust."""
        # self.client on nagu 'requests' teek, aga Locust haldab seda.
        self.client.get("/fast")

    @task(2) # See tegevus on 2x tõenäolisem
    def visit_medium_page(self):
        """See funktsioon simuleerib keskmise kiirusega lehe külastust."""
        self.client.get("/medium")

    @task(1) # See tegevus on kõige vähem tõenäoline
    def visit_slow_page(self):
        """See funktsioon simuleerib aeglase lehe külastust."""
        self.client.get("/slow")
