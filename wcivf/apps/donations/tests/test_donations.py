def test_donation_middleware_form_valid(db, client):

    req = client.get("/donate/")
    assert req.status_code == 200
