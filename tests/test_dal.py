# -*- coding: utf-8 -*-
"""
    tests.dal
    ---------

    pyDAL implementation over weppy.

    :copyright: (c) 2015 by Giovanni Barillari
    :license: BSD, see LICENSE for more details.
"""

import pytest
from pydal.objects import Table

from weppy import App, sdict
from weppy.dal import DAL, Field, Model, Prop, computation, before_insert, \
    after_insert, before_update, after_update, before_delete, after_delete, \
    virtualfield, fieldmethod, modelmethod, has_one, has_many, belongs_to
from weppy.validators import isntEmpty, notInDb


def _represent_f(value):
    return value


def _widget_f(field, value):
    return value


def _call_bi(fields):
    return fields[:-1]


def _call_ai(fields, id):
    return fields[:-1], id+1


def _call_u(set, fields):
    return set, fields[:-1]


def _call_d(set):
    return set


class Stuff(Model):
    a = Prop('string')
    b = Prop()
    price = Prop('double')
    quantity = Prop('integer')
    total = Prop('double')
    invisible = Prop()

    validators = {
        "a": isntEmpty()
    }

    visibility = {
        "invisible": (False, False)
    }

    labels = {
        "a": "A label"
    }

    comments = {
        "a": "A comment"
    }

    updates = {
        "a": "a_update"
    }

    representation = {
        "a": _represent_f
    }

    widgets = {
        "a": _widget_f
    }

    def setup(self):
        self.entity.b.requires = notInDb(self.db, self.entity.b)

    @computation('total')
    def eval_total(self, row):
        return row.price*row.quantity

    @before_insert
    def bi(self, fields):
        return _call_bi(fields)

    @after_insert
    def ai(self, fields, id):
        return _call_ai(fields, id)

    @before_update
    def bu(self, set, fields):
        return _call_u(set, fields)

    @after_update
    def au(self, set, fields):
        return _call_u(set, fields)

    @before_delete
    def bd(self, set):
        return _call_d(set)

    @after_delete
    def ad(self, set):
        return _call_d(set)

    @virtualfield('totalv')
    def eval_total_v(self, row):
        return row.stuffs.price*row.stuffs.quantity

    @fieldmethod('totalm')
    def eval_total_m(self, row):
        return row.stuffs.price*row.stuffs.quantity

    @modelmethod
    def method_test(db, entity, t):
        return db, entity, t


class Person(Model):
    has_many('things')

    name = Prop()
    age = Prop('integer')


class Thing(Model):
    belongs_to('person')
    has_many('features')

    name = Prop()
    color = Prop()


class Feature(Model):
    belongs_to('thing')
    has_one('price')

    name = Prop()


class Price(Model):
    belongs_to('feature')

    value = Prop('integer')


@pytest.fixture(scope='module')
def db():
    app = App(__name__)
    db = DAL(app)
    db.define_models([Stuff, Person, Thing, Feature, Price])
    return db


def test_db_instance(db):
    assert isinstance(db, DAL)


def test_table_definition(db):
    assert isinstance(db.Stuff, Table)
    assert isinstance(db[Stuff.tablename], Table)


def test_fields(db):
    assert isinstance(db.Stuff.a, Field)
    assert db.Stuff.a.type == "string"


def test_validators(db):
    assert isinstance(db.Stuff.a.requires, isntEmpty)


def test_visibility(db):
    assert db.Stuff.a.readable is True
    assert db.Stuff.a.writable is True
    assert db.Stuff.invisible.readable is False
    assert db.Stuff.invisible.writable is False


def test_labels(db):
    assert db.Stuff.a.label == "A label"


def test_comments(db):
    assert db.Stuff.a.comment == "A comment"


def test_updates(db):
    assert db.Stuff.a.update == "a_update"


def test_representation(db):
    assert db.Stuff.a.represent == _represent_f


def test_widgets(db):
    assert db.Stuff.a.widget == _widget_f


def test_set_helper(db):
    assert isinstance(db.Stuff.b.requires, notInDb)


def test_computations(db):
    row = sdict(price=12.95, quantity=3)
    rv = db.Stuff.total.compute(row)
    assert rv == 12.95*3


def test_callbacks(db):
    fields = ["a", "b", "c"]
    id = 12
    rv = db.Stuff._before_insert[-1](fields)
    assert rv == fields[:-1]
    rv = db.Stuff._after_insert[-1](fields, id)
    assert rv[0] == fields[:-1] and rv[1] == id+1
    set = {"a": "b"}
    rv = db.Stuff._before_update[-1](set, fields)
    assert rv[0] == set and rv[1] == fields[:-1]
    rv = db.Stuff._after_update[-1](set, fields)
    assert rv[0] == set and rv[1] == fields[:-1]
    rv = db.Stuff._before_delete[-1](set)
    assert rv == set
    rv = db.Stuff._after_delete[-1](set)
    assert rv == set


def test_virtualfields(db):
    db.Stuff._before_insert = []
    db.Stuff._after_insert = []
    db.Stuff.insert(a="foo", b="bar", price=12.95, quantity=3)
    db.commit()
    row = db(db.Stuff.id > 0).select().first()
    assert row.totalv == 12.95*3


def test_fieldmethods(db):
    row = db(db.Stuff.id > 0).select().first()
    assert row.totalm() == 12.95*3


def test_modelmethods(db):
    tm = "foo"
    rv = Stuff.method_test(tm)
    assert rv[0] == db and rv[1] == db.Stuff and rv[2] == tm


def test_relations(db):
    p = db.Person.insert(name="Giovanni", age=25)
    t = db.Thing.insert(name="apple", color="red", person=p)
    f = db.Feature.insert(name="tasty", thing=t)
    db.Price.insert(value=5, feature=f)
    p = db.Person(name="Giovanni")
    t = p.things()
    assert len(t) == 1
    assert t[0].name == "apple" and t[0].color == "red" and \
        t[0].person.id == p.id
    f = p.things()[0].features()
    assert len(f) == 1
    assert f[0].name == "tasty" and f[0].thing.id == t[0].id and \
        f[0].thing.person.id == p.id
    #m = p.things()[0].features()[0].price
    #assert m.value == 5 and m.feature.id == f[0].id and \
    #    m.feature.thing.id == t[0].id and m.feature.thing.person.id == p.id
