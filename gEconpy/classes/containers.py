import sympy as sp

from gEconpy.classes.time_aware_symbol import TimeAwareSymbol
from gEconpy.shared.utilities import (
    float_values_to_sympy_float,
    sort_dictionary,
    string_keys_to_sympy,
    sympy_keys_to_strings,
    sympy_number_values_to_floats,
)


class SymbolDictionary(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.is_sympy: bool = False
        self._assumptions: dict = {}

        keys = list(self.keys())
        if any([not isinstance(x, (sp.Symbol, str)) for x in keys]):
            raise KeyError("All keys should be either string or Sympy symbols")

        if len(keys) > 0:
            self.is_sympy = not isinstance(keys[0], str)

            if self.is_sympy and any([isinstance(x, str) for x in keys]):
                raise KeyError("Cannot mix sympy and string keys")
            if not self.is_sympy and any([isinstance(x, sp.Symbol) for x in keys]):
                raise KeyError("Cannot mix sympy and string keys")

        self._save_assumptions(keys)

    def __or__(self, other):
        if not isinstance(other, dict):
            raise ValueError("__or__ not defined on non-dictionary objects")
        if not isinstance(other, SymbolDictionary):
            other = SymbolDictionary(other)

        d_copy = self.copy()

        # If one dict or the other is empty, only merge assumptions
        if len(d_copy.keys()) == 0:
            other_copy = other.copy()
            other_copy._assumptions.update(self._assumptions)
            return other_copy

        if len(other.keys()) == 0:
            d_copy._assumptions.update(other._assumptions)
            return d_copy

        # If both are populated but of different types, raise an error
        if other.is_sympy != self.is_sympy:
            raise ValueError(
                "Cannot merge string-mode SymbolDictionary with sympy-mode SymbolDictionary"
            )

        # Full merge
        other_assumptions = getattr(other, "_assumptions", {})

        d_copy.update(other)
        d_copy._assumptions.update(other_assumptions)

        return d_copy

    def copy(self):
        new_d = SymbolDictionary(super().copy())
        new_d.is_sympy = self.is_sympy
        new_d._assumptions = self._assumptions

        return new_d

    def _save_assumptions(self, keys):
        if not self.is_sympy:
            return
        if not isinstance(keys, list):
            keys = [keys]
        for key in keys:
            if isinstance(key, TimeAwareSymbol):
                self._assumptions[key.base_name] = key.assumptions0
            else:
                self._assumptions[key.name] = key.assumptions0

    def __setitem__(self, key, value):
        if len(self.keys()) == 0:
            self.is_sympy = isinstance(key, sp.Symbol)
        elif self.is_sympy and not isinstance(key, sp.Symbol):
            raise KeyError("Cannot add string key to dictionary in sympy mode")
        elif not self.is_sympy and isinstance(key, sp.Symbol):
            raise KeyError("Cannot add sympy key to dictionary in string mode")
        super().__setitem__(key, value)
        self._save_assumptions(key)

    def _clean_update(self, d):
        self.clear()
        self._assumptions.clear()

        self.update(d)
        self._assumptions.update(d._assumptions)
        self.is_sympy = d.is_sympy

    def to_sympy(self, inplace=False, new_assumptions=None):
        new_assumptions = new_assumptions or {}

        assumptions = self._assumptions.copy()
        assumptions.update(new_assumptions)

        d = SymbolDictionary(string_keys_to_sympy(self, assumptions))

        if inplace:
            self._clean_update(d)
            return

        return d

    def _step_dict_keys(self, func_name):
        is_sympy = self.is_sympy
        dict_copy = self.copy()
        if not is_sympy:
            dict_copy.to_sympy(inplace=True)

        d = {}
        for k, v in dict_copy.items():
            if hasattr(k, func_name):
                d[getattr(k, func_name)()] = v
            else:
                d[k] = v

        d = SymbolDictionary(d)
        if not is_sympy:
            d.to_string(inplace=True)

        return d

    def step_backward(self, inplace=False):
        d = self._step_dict_keys("step_backward")

        if inplace:
            self._clean_update(d)
            return
        else:
            return d

    def step_forward(self, inplace=False):
        d = self._step_dict_keys("step_forward")

        if inplace:
            self._clean_update(d)
            return
        else:
            return d

    def to_ss(self, inplace=False):
        d = self._step_dict_keys("to_ss")

        if inplace:
            self._clean_update(d)
            return
        else:
            return d

    def to_string(self, inplace=False):
        copy_dict = self.copy()
        d = SymbolDictionary(sympy_keys_to_strings(copy_dict))
        d._assumptions = copy_dict._assumptions.copy()

        if inplace:
            self._clean_update(d)
            return

        return d

    def sort_keys(self, inplace=False):
        is_sympy = self.is_sympy
        d = SymbolDictionary(sort_dictionary(self.copy().to_string()))
        d._assumptions = self._assumptions.copy()

        if is_sympy:
            d = d.to_sympy()

        if inplace:
            self._clean_update(d)
            return

        return d

    def values_to_float(self, inplace=False):
        d = self.copy()
        d = sympy_number_values_to_floats(d)
        d._assumptions = self._assumptions.copy()

        if inplace:
            self._clean_update(d)
            return

        return d

    def float_to_values(self, inplace=False):
        d = self.copy()
        d = float_values_to_sympy_float(d)
        d._assumptions = self._assumptions.copy()

        if inplace:
            self._clean_update(d)
            return

        return d
