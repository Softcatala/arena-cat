def test_get_categories_returns_catalog_sorted_by_code(client):
    response = client.get("/api/categories")

    assert response.status_code == 200
    assert response.json() == {
        "categories": [
            {
                "code": "correccio",
                "name": "Correcció",
                "description": "Corregeix aquest text.",
            },
            {
                "code": "reformulacio",
                "name": "Reformulació",
                "description": "Reformula aquest text.",
            },
            {
                "code": "traduccio",
                "name": "Traducció",
                "description": "Tradueix aquest text.",
            },
        ]
    }
