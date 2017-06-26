#!/usr/bin/env python
# encoding: utf-8

import warnings
import os
import inspect
from functools import wraps

import pytest
from unittest import TestCase

from marvin import config, marvindb
from marvin.core.exceptions import MarvinSkippedTestWarning
from marvin.api.api import Interaction
from marvin.tools.maps import _get_bintemps


def use_bintypes(*bintypes):
    """Decorates test to run only for the given bintypes."""
    def check_bintype(f):
        @wraps(f)
        def decorated_function(self, *args, **kwargs):
            if kwargs['galaxy'].bintype not in bintypes:
                pytest.skip('Only use {}'.format(', '.join(bintypes)))
            return f(self, *args, **kwargs)
        return decorated_function
    return check_bintype


def use_releases(*releases):
    """Decorates test to run only for the given releases."""
    def check_bintype(f):
        @wraps(f)
        def decorated_function(self, *args, **kwargs):
            if 'release' in kwargs.keys():
                release = kwargs['release']
            elif 'galaxy' in kwargs.keys():
                release = kwargs['galaxy'].release
            if release not in releases:
                pytest.skip('Only use {}'.format(', '.join(releases)))
            return f(self, *args, **kwargs)
        return decorated_function
    return check_bintype


class MetaUse(object):
    ''' Meta class to define a testing class that decorates all tests to use the specified fxn '''
    def __init__(self, *args):
        self.args = args

    def __call__(self, decorated_class):
        for attr in inspect.getmembers(decorated_class, inspect.isfunction):
            # only decorate public functions
            if attr[0][0] != '_':
                setattr(decorated_class, attr[0],
                        self.fxn(*self.args)(getattr(decorated_class, attr[0])))
        return decorated_class


UseBintypes = type('UseBintypes', (MetaUse,), {'fxn': use_bintypes})
UseReleases = type('UseReleases', (MetaUse,), {'fxn': use_releases})


# These decorators for functions and classes allow to skip or run tests only for galaxies
# that have certain bintypes, templates, or releases
def marvin_test_if(mode='skip', **kfilter):
    """Decorates test to skip/include certain parameters.

    Parameters:
        mode ({'skip', 'include', 'xfail'}):
            Whether the decorator should skip the test if it matches the filter
            conditions, include it only if it matches the conditions, or mark
            it as an expected failure.
        kfilter (kwargs):
            A keyword argument whose name should match one of the fixtures in
            the test. If the fixture returns a single value, the keyword must
            define a list of the fixture values to skip, include, or xfail.
            If the fixture returns an object, the value of the kwarg must be a
            dictionary of the object attributes to filter on. The ``mode`` is
            applied to all the attributes in the dictionary equally.

    Examples:
        If you want to only test for galaxies with bintype ``'STON'`` and
        template ``'MILES-THIN'`` you can do::

            @marvin_skip_if(galaxy=dict(bintype=['STON'], template=['MILES-THIN']), mode='include')

        You can also mark all tests with ``data_origin='file'`` as expected
        failure::

            @marvin_skip_if(data_origin=['file'], mode='xfails')

        ``marvin_skip_if`` decorators can be concatenated::

            @marvin_skip_if(data_origin=['file'], mode='xfails')
            @marvin_skip_if(galaxy=dict(bintype=['SPX']), mode='skip')

        will skip ``'SPX'`` bintypes and expect a failure on ``'file'``
        data_origins.

    """

    def check_params(ff):

        def _should_skip(filter_values, fixture_value, prop_name):
            ll = ', '.join(filter_values)
            if mode == 'skip' and fixture_value in filter_values:
                return pytest.skip('Skipping {0}={1!r}'.format(prop_name, ll))
            elif mode == 'include' and fixture_value not in filter_values:
                return pytest.skip('Skipping all {0} except {1!r}'.format(prop_name, ll))
            elif mode == 'xfail' and fixture_value in filter_values:
                return pytest.xfail('Expected failure if {0}={1!r}'.format(prop_name, ll))
            return False

        @wraps(ff)
        def decorated_function(self, *args, **kwargs):

            assert mode in ['skip', 'include', 'xfail'], \
                'valid modes are \'skip\', \'include\', and \'xfail\''

            if len(kfilter) > 1:
                raise ValueError('marvin_skip_if only accepts one filter condition.')

            fixture_to_filter, filter_attributes = list(kfilter.items())[0]

            if fixture_to_filter not in kwargs:
                return ff(self, *args, **kwargs)

            if not isinstance(filter_attributes, dict):
                _should_skip(filter_attributes, kwargs[fixture_to_filter], fixture_to_filter)
            else:
                for filter_attribute, filter_values in filter_attributes.items():
                    fixture = kwargs[fixture_to_filter]
                    if not hasattr(fixture, filter_attribute):
                        continue
                    fixture_value = getattr(fixture, filter_attribute)
                    if _should_skip(filter_values, fixture_value, filter_attribute):
                        break

            return ff(self, *args, **kwargs)
        return decorated_function
    return check_params


class marvin_test_if_class(object):
    """Decorate all tests in a class to run only for, or skip, certain parameters.

    See ``marvin_test_if``. This decorator is the equivalent for decorating
    classes isntead of functions.

    """

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __call__(self, decorated_class):
        for attr in inspect.getmembers(decorated_class, inspect.isfunction):
            # only decorate public functions
            if attr[0][0] != '_':
                setattr(decorated_class, attr[0],
                        marvin_test_if(*self.args,
                                       **self.kwargs)(getattr(decorated_class, attr[0])))
        return decorated_class


# Decorator to skip a test if the session is None (i.e., if there is no DB)
def skipIfNoDB(test):
    @wraps(test)
    def wrapper(self, db, *args, **kwargs):
        if db.session is None:
            pytest.skip('Skip because no DB.')
        else:
            return test(self, db, *args, **kwargs)
    return wrapper



