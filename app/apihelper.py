from flask import json, url_for
from sqlalchemy.orm.attributes import QueryableAttribute
from sqlalchemy.sql.expression import not_
from app import db


class PaginatedApiMixin:
    """
    Klasa, umożliwiająca podzielenie wyników zapytania na strony.
    Wzięta z rozdziału ostatniego o API
    Na podstawie podobnego rozwiązania z rozdziału 16
    Na razie wpisałem część funkcjonalności...
    """
    @staticmethod
    def to_collection_dict(query, page, per_page, endpoint, **kwargs):
        resources = query.paginate(page, per_page, error_out=False)
        data = {
            'items': [item.to_dict(**kwargs) for item in resources.items],
            'meta': {
                'page': page,
                'per_page': per_page,
                'total_pages': resources.pages,
                'total_items': resources.total
            },
            'links': {
                'self': url_for(endpoint, page=page, per_page=per_page, **kwargs),
                'next': url_for(endpoint, page=page + 1, per_page=per_page, **kwargs) if resources.has_next else None,
                'prev': url_for(endpoint, page=page - 1, per_page=per_page, **kwargs) if resources.has_prev else None
            }
        }
        return data


class ApiBaseModel(db.Model):
    __abstract__ = True

    def __init__(self, **kwargs):
        kwargs['_force'] = True
        self.from_dict(**kwargs)

    _default_fields = []
    _hidden_fields = []
    _readonly_fields = []

    def to_dict(self, show=None, _hide=None, _path=None):
        """
        Return a dictionary representation of this model.
        It returns 'id', 'created_at' and 'modified_at' always.
        Class can use it's own '_default_fields', '_hidden_fields' and '_readonly_fields' lists.
        :param show: list of attributes added to default list
        :param _hide: list of attributes added to hidden list
        :param _path: ???
        :return: dictionary with selected fields
        """

        show = show or []
        _hide = _hide or []

        hidden = self._hidden_fields if hasattr(self, '_hidden_fields') else []
        default = self._default_fields if hasattr(self, '_default_fields') else []
        default.extend(['id', 'modified_at', 'created_at', '_links'])

        if not _path:
            _path = self.__tablename__.lower()

            def prepend_path(path_item):
                path_item = path_item.lower()
                if path_item.split('.', 1)[0] == _path:
                    return path_item
                if len(path_item) == 0:
                    return path_item
                if path_item[0] != '.':
                    path_item = f'.{path_item}'
                path_item = f'{_path}{path_item}'
                return path_item

            _hide[:] = [prepend_path(x) for x in _hide]
            show[:] = [prepend_path(x) for x in show]

        columns = self.__table__.columns.keys()
        relationships = self.__mapper__.relationships.keys()
        properties = dir(self)

        ret_data = {}

        for key in columns:
            if key.startswith('_'):
                continue
            check = f'{_path}.{key}'
            if check in _hide or key in hidden:
                continue
            if check in show or key in default:
                ret_data[key] = getattr(self, key)

        for key in relationships:
            if key.startswith('_'):
                continue
            check = f'{_path}.{key}'
            if check in _hide or key in hidden:
                continue
            if check in show or key in default:
                _hide.append(check)
                is_list = self.__mapper__.relationships[key].uselist
                if is_list:
                    items = getattr(self, key)
                    if self.__mapper__.relationships[key].query_class is not None:
                        if hasattr(items, 'all'):
                            items = items.all()
                    ret_data[key] = []
                    for item in items:
                        ret_data[key].append(item.to_dict(show=list(show),
                                                          _hide=list(_hide),
                                                          _path=f'{_path}.{key.lower()}'))
                else:
                    if (
                        self.__mapper__.relationships[key].query_class is not None
                        or self.__mapper__.relationships[key].instrument_class is not None
                    ):
                        item = getattr(self, key)
                        if item is not None:
                            ret_data[key] = item.to_dict(show=list(show),
                                                         _hide=list(_hide),
                                                         _path=f'{_path}.{key.lower()}')
                        else:
                            ret_data[key] = None
                    else:
                        ret_data[key] = getattr(self, key)

        for key in list(set(properties) - set(columns) - set(relationships)):
            if key.startswith('_'):
                continue
            if not hasattr(self.__class__, key):
                continue
            attr = getattr(self.__class__, key)
            if not (isinstance(attr, property) or isinstance(attr, QueryableAttribute)):
                continue
            check = f'{_path}.{key}'
            if check in _hide or key in hidden:
                continue
            if check in show or key in default:
                val = getattr(self, key)
                if hasattr(val, 'to_dict'):
                    ret_data[key] = val.to_dict(show=list(show),
                                                _hide=list(_hide),
                                                _path=f'{_path}.{key.lower()}')
                else:
                    try:
                        ret_data[key] = json.loads(json.dumps(val))
                    except:
                        pass

        return ret_data

    def from_dict(self, **kwargs):
        """
        Update this model with a dictionary.
        Don't update: 'id', 'created_at', 'modified_at' and from lists: '_readonly_fields' and '_hidden_fields'
        :param kwargs: attributes to update
        :return: dictionary with changes
        """

        _force = kwargs.pop('_force', False)

        readonly = self._readonly_fields if hasattr(self, '_readonly_fields') else []
        if hasattr(self, '_hidden_fields'):
            readonly += self._hidden_fields

        readonly += ['id', 'created_at', 'modified_at']

        columns = self.__table__.columns.keys()
        relationships = self.__mapper__.relationships.keys()
        properties = dir(self)

        changes = {}

        for key in columns:
            if key.startswith('_'):
                continue
            allowed = True if _force or key not in readonly else False
            exists = True if key in kwargs else False
            if allowed and exists:
                val = getattr(self, key)
                if val != kwargs[key]:
                    changes[key] = {'old': val, 'new': kwargs[key]}
                    setattr(self, key, kwargs[key])

        for rel in relationships:
            if rel.startswith('_'):
                continue
            allowed = True if _force or rel not in readonly else False
            exists = True if rel in kwargs else False
            if allowed and exists:
                is_list = self.__mapper__.relationships[rel].uselist
                if is_list:
                    valid_ids = []
                    query = getattr(self, rel)
                    cls = self.__mapper__.relationships[rel].argument()
                    for item in kwargs[rel]:
                        if (
                            'id' in item
                            and query.filter_by(id=item['id']).limit(1).count() == 1
                        ):
                            obj = cls.query.filter_by(id=item['id']).first()
                            col_changes = obj.from_dict(**item)
                            if col_changes:
                                col_changes['id'] = str(item['id'])
                                if rel in changes:
                                    changes[rel].append(col_changes)
                                else:
                                    changes.update({rel: [col_changes]})
                            valid_ids.append(str(item['id']))
                        else:
                            col = cls()
                            col_changes = col.from_dict(**item)
                            query.append(col)
                            db.session.flush()
                            if col_changes:
                                col_changes['id'] = str(col.id)
                                if rel in changes:
                                    changes[rel].append(col_changes)
                                else:
                                    changes.update({rel: [col_changes]})
                            valid_ids.append(str(col.id))

                    # delete rows from relationship that were not in kwargs[rel]
                    for item in query.filter(not_(cls.id.in_(valid_ids))).all():
                        col_changes = {'id': str(item.id), 'deleted': True}
                        if rel in changes:
                            changes[rel].append(col_changes)
                        else:
                            changes.update({rel: [col_changes]})
                        db.session.delete(item)

                else:
                    val = getattr(self, rel)
                    if self.__mapper__.relationships[rel].query_class is not None:
                        if val is not None:
                            col_changes = val.from_dict(**kwargs[rel])
                            if col_changes:
                                changes.update({rel: col_changes})
                    else:
                        if val != kwargs[rel]:
                            setattr(self, rel, kwargs[rel])
                            changes[rel] = {'old': val, 'new': kwargs[rel]}

        for key in list(set(properties) - set(columns) - set(relationships)):
            if key.startswith('_'):
                continue
            allowed = True if _force or key not in readonly else False
            exists = True if key in kwargs else False
            if allowed and exists and getattr(self.__class__, key).fset is not None:
                val = getattr(self, key)
                if hasattr(val, 'to_dict'):
                    val = val.to_dict()
                changes[key] = {'old': val, 'new': kwargs[key]}
                setattr(self, key, kwargs[key])

        return changes