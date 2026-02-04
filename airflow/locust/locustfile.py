from locust import HttpUser, task, between

class StreamlitUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def load_homepage(self):
        self.client.get("/")

    @task(3)
    def search_trip(self):
        self.client.get("/?city=Paris&start_date=2026-12-01&stay_duration=3")

    @task(2)
    def view_chatbot(self):
        self.client.get("/?page=%E2%9A%96%20Chatbot")

    @task
    def test_chatbot(self):
        self.client.post("/chatbot", json={
            "prompt": "Je vais à Paris du 15 au 18 juin 2026. Quels sont les événements recommandés ?"
        })
