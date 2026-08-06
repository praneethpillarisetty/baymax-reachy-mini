from baymax.safety import SafetyEngine


def test_emergency_response_requires_no_model():
    response = SafetyEngine().check("They are unconscious and will not wake")
    assert response is not None
    assert "emergency services" in response.message
