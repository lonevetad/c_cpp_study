import math
import pytest
from fcpp_py import Vec2, Vec3, version


# ── version ───────────────────────────────────────────────────────────

def test_version():
    v = version()
    assert isinstance(v, str)
    assert len(v) > 0


# ── Vec2 construction ─────────────────────────────────────────────────

def test_vec2_default():
    v = Vec2()
    assert v[0] == 0.0 and v[1] == 0.0

def test_vec2_construction():
    v = Vec2(3.0, 4.0)
    assert v[0] == 3.0 and v[1] == 4.0

def test_vec2_properties():
    v = Vec2(3.0, 4.0)
    assert v.x == 3.0 and v.y == 4.0

def test_vec2_setitem():
    v = Vec2(1.0, 2.0)
    v[0] = 9.0
    assert v[0] == 9.0

def test_vec2_len():
    assert len(Vec2()) == 2

def test_vec2_iter():
    v = Vec2(1.0, 2.0)
    assert list(v) == pytest.approx([1.0, 2.0])

def test_vec2_repr():
    v = Vec2(1.0, 2.0)
    assert "Vec2" in repr(v)


# ── Vec2 norm / distance ──────────────────────────────────────────────

def test_vec2_norm_345():
    assert Vec2(3.0, 4.0).norm() == pytest.approx(5.0)

def test_vec2_norm_zero():
    assert Vec2(0.0, 0.0).norm() == pytest.approx(0.0)

def test_vec2_norm_unit_x():
    assert Vec2(1.0, 0.0).norm() == pytest.approx(1.0)

def test_vec2_distance_345():
    assert Vec2(0.0, 0.0).distance(Vec2(3.0, 4.0)) == pytest.approx(5.0)

def test_vec2_distance_same():
    v = Vec2(1.0, 2.0)
    assert v.distance(v) == pytest.approx(0.0)

def test_vec2_distance_symmetric():
    a, b = Vec2(1.0, 2.0), Vec2(4.0, 6.0)
    assert a.distance(b) == pytest.approx(b.distance(a))


# ── Vec2 dot ──────────────────────────────────────────────────────────

def test_vec2_dot_orthogonal():
    assert Vec2(1.0, 0.0).dot(Vec2(0.0, 1.0)) == pytest.approx(0.0)

def test_vec2_dot_parallel():
    v = Vec2(3.0, 4.0)
    assert v.dot(v) == pytest.approx(25.0)

def test_vec2_dot_value():
    assert Vec2(1.0, 2.0).dot(Vec2(3.0, 4.0)) == pytest.approx(11.0)


# ── Vec2 arithmetic ───────────────────────────────────────────────────

def test_vec2_add():
    c = Vec2(1.0, 2.0) + Vec2(3.0, 4.0)
    assert c[0] == pytest.approx(4.0) and c[1] == pytest.approx(6.0)

def test_vec2_sub():
    c = Vec2(3.0, 4.0) - Vec2(1.0, 1.0)
    assert c[0] == pytest.approx(2.0) and c[1] == pytest.approx(3.0)

def test_vec2_mul():
    c = Vec2(2.0, 3.0) * 2.0
    assert c[0] == pytest.approx(4.0) and c[1] == pytest.approx(6.0)

def test_vec2_rmul():
    c = 2.0 * Vec2(2.0, 3.0)
    assert c[0] == pytest.approx(4.0) and c[1] == pytest.approx(6.0)

def test_vec2_div():
    c = Vec2(4.0, 6.0) / 2.0
    assert c[0] == pytest.approx(2.0) and c[1] == pytest.approx(3.0)

def test_vec2_neg():
    c = -Vec2(1.0, -2.0)
    assert c[0] == pytest.approx(-1.0) and c[1] == pytest.approx(2.0)

def test_vec2_add_does_not_mutate():
    a = Vec2(1.0, 2.0)
    _ = a + Vec2(3.0, 4.0)
    assert a[0] == 1.0 and a[1] == 2.0


# ── Vec2 unit ─────────────────────────────────────────────────────────

def test_vec2_unit_norm():
    u = Vec2(3.0, 4.0).unit()
    assert u.norm() == pytest.approx(1.0)

def test_vec2_unit_values():
    u = Vec2(3.0, 4.0).unit()
    assert u[0] == pytest.approx(0.6) and u[1] == pytest.approx(0.8)

def test_vec2_unit_x():
    u = Vec2(5.0, 0.0).unit()
    assert u[0] == pytest.approx(1.0) and u[1] == pytest.approx(0.0)


# ── Vec2 equality ─────────────────────────────────────────────────────

def test_vec2_eq_equal():
    assert Vec2(1.0, 2.0) == Vec2(1.0, 2.0)

def test_vec2_eq_not_equal():
    assert Vec2(1.0, 2.0) != Vec2(1.0, 3.0)

def test_vec2_eq_wrong_type():
    assert Vec2(1.0, 2.0).__eq__("x") is NotImplemented


# ── Vec3 construction ─────────────────────────────────────────────────

def test_vec3_default():
    v = Vec3()
    assert v[0] == 0.0 and v[1] == 0.0 and v[2] == 0.0

def test_vec3_construction():
    v = Vec3(1.0, 2.0, 3.0)
    assert v[0] == 1.0 and v[1] == 2.0 and v[2] == 3.0

def test_vec3_properties():
    v = Vec3(1.0, 2.0, 3.0)
    assert v.x == 1.0 and v.y == 2.0 and v.z == 3.0

def test_vec3_setitem():
    v = Vec3(1.0, 2.0, 3.0)
    v[2] = 9.0
    assert v[2] == 9.0

def test_vec3_len():
    assert len(Vec3()) == 3

def test_vec3_iter():
    v = Vec3(1.0, 2.0, 3.0)
    assert list(v) == pytest.approx([1.0, 2.0, 3.0])

def test_vec3_repr():
    assert "Vec3" in repr(Vec3(1.0, 2.0, 3.0))


# ── Vec3 norm / distance ──────────────────────────────────────────────

def test_vec3_norm():
    assert Vec3(1.0, 2.0, 2.0).norm() == pytest.approx(3.0)  # sqrt(1+4+4)

def test_vec3_norm_zero():
    assert Vec3(0.0, 0.0, 0.0).norm() == pytest.approx(0.0)

def test_vec3_distance():
    assert Vec3(0.0, 0.0, 0.0).distance(Vec3(1.0, 2.0, 2.0)) == pytest.approx(3.0)

def test_vec3_distance_symmetric():
    a, b = Vec3(1.0, 2.0, 3.0), Vec3(4.0, 5.0, 6.0)
    assert a.distance(b) == pytest.approx(b.distance(a))


# ── Vec3 dot ──────────────────────────────────────────────────────────

def test_vec3_dot_orthogonal():
    assert Vec3(1.0, 0.0, 0.0).dot(Vec3(0.0, 1.0, 0.0)) == pytest.approx(0.0)

def test_vec3_dot_value():
    assert Vec3(1.0, 2.0, 3.0).dot(Vec3(4.0, 5.0, 6.0)) == pytest.approx(32.0)


# ── Vec3 arithmetic ───────────────────────────────────────────────────

def test_vec3_add():
    c = Vec3(1.0, 2.0, 3.0) + Vec3(4.0, 5.0, 6.0)
    assert list(c) == pytest.approx([5.0, 7.0, 9.0])

def test_vec3_sub():
    c = Vec3(4.0, 5.0, 6.0) - Vec3(1.0, 2.0, 3.0)
    assert list(c) == pytest.approx([3.0, 3.0, 3.0])

def test_vec3_mul():
    c = Vec3(1.0, 2.0, 3.0) * 3.0
    assert list(c) == pytest.approx([3.0, 6.0, 9.0])

def test_vec3_rmul():
    c = 3.0 * Vec3(1.0, 2.0, 3.0)
    assert list(c) == pytest.approx([3.0, 6.0, 9.0])

def test_vec3_div():
    c = Vec3(3.0, 6.0, 9.0) / 3.0
    assert list(c) == pytest.approx([1.0, 2.0, 3.0])

def test_vec3_neg():
    c = -Vec3(1.0, -2.0, 3.0)
    assert list(c) == pytest.approx([-1.0, 2.0, -3.0])

def test_vec3_add_does_not_mutate():
    a = Vec3(1.0, 2.0, 3.0)
    _ = a + Vec3(4.0, 5.0, 6.0)
    assert list(a) == pytest.approx([1.0, 2.0, 3.0])


# ── Vec3 unit ─────────────────────────────────────────────────────────

def test_vec3_unit_norm():
    assert Vec3(1.0, 2.0, 2.0).unit().norm() == pytest.approx(1.0)

def test_vec3_unit_values():
    u = Vec3(1.0, 2.0, 2.0).unit()
    assert u[0] == pytest.approx(1.0/3.0)
    assert u[1] == pytest.approx(2.0/3.0)
    assert u[2] == pytest.approx(2.0/3.0)


# ── Vec3 equality ─────────────────────────────────────────────────────

def test_vec3_eq_equal():
    assert Vec3(1.0, 2.0, 3.0) == Vec3(1.0, 2.0, 3.0)

def test_vec3_eq_not_equal():
    assert Vec3(1.0, 2.0, 3.0) != Vec3(1.0, 2.0, 4.0)

def test_vec3_eq_wrong_type():
    assert Vec3(1.0, 2.0, 3.0).__eq__("x") is NotImplemented
