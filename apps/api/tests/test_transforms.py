from app.transforms import normalize_email, normalize_phone, normalize_plate, validate_rut


def test_validate_known_rut():
    result = validate_rut("12.345.678-5")
    assert result["valid"] is True
    assert result["normalized"] == "12.345.678-5"


def test_email_cl_detection():
    result = normalize_email("Persona@empresa.cl")
    assert result["valid"] is True
    assert result["is_cl"] is True
    assert result["domain"] == "empresa.cl"


def test_phone_normalization():
    result = normalize_phone("9 8765 4321")
    assert result["normalized"] == "+56987654321"
    assert result["country"] == "CL"


def test_plate_normalization():
    result = normalize_plate("BB-CC-11")
    assert result["normalized"] == "BBCC11"
    assert result["valid_shape"] is True
