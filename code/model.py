#-*- coding: utf-8 -*-
import re
import yaml
import itertools as it
from helpers import Container
from slot import SlotScheme

class Model (object):
    '''Initialization with yaml:
"
data:
    par1: [val11, val12]
    par2: val21
    par3:
      par3_1: [val311, val312]
      par3_2:
        par3_2_1: val321
    par3__par3_3: [val331]
scheme:
    __2:
    - par3__par3_1
    - par1
    - __3:
      - par3__par3_2__par3_2_1
      - par1
      - par2
constraints:
    optional:
      - "lambda par1, par2: par1 > par2"
      - "lambda par1, par2: par1 < par2 * 2"
    mandatory:
      - "lambda par3__par3_3, par3__par3_2__par3_2_1, par1: par1 not in (par3__par3_2__par_3_2_1, par3__par3_3)"
priority:
    par1:
      val12: 5
    par3:
      par3_3: 10
    par3__par3_2__par3_2_1: 3"

Data after initialization:
<Model object>:
  data -> {
    par1: [val11, val12]
    par2: [val21]
    par3__par3_1: [val311, val312]
    par3__par3_2__par_3_2_1: [val321]
    par3__par3_3: [val331]
  }
  params -> [par1, par2, par3__par3_1, par3__par3_2, par3__par3_3]
  scheme -> {
    __2:
    - par3__par3_1
    - par1
    - __3:
      - par3__par3_2__par3_2_1
      - par1
      - par2
  }
  constraints -> {
    optional:
      par1,par2: [<function>, <function>]
    mandatory:
      par1,par3__par3_2__par3_2_1,par3__par3_3: [<function>]
  }
  priority -> {
    par1__val12: 5
    par3__par3_3: 10
    par3__par3_2__par3_2_1: 3
  }
'''
    arg_sep = re.compile("\s*,\s*")
    lambda_signature_re = re.compile("^lambda\s+(.*)\s*:(.*)") # regexp for lambda arguments match
    def __init__ (self, yaml_model):
        self.parse(yaml_model)

    def parse (self, yaml_model):
        def flatten_inner (data):
            '''Changes nested paths to flat with '__' as parent-child divisor. Works inplace.'''
            for k, v in data.items():
                if isinstance(v, dict):
                    for kk, vv in flatten_inner(v).iteritems():
                        data["%s__%s" % (k, kk)] = vv
                    data.pop(k)
            return data

        def turn_values_to_list (data):
            '''Puts scalar values into single-value list. Works inplace.'''
            for k, v in data.iteritems():
                if not isinstance(v, (list, dict)):
                    data[k] = [v]
                elif isinstance(v, dict):
                    turn_values_to_list(v)
            return data
            
        def _parse_constraints (constraints):
            parsed = {}
            for c_lambda in constraints:
                (sig, body) = self.lambda_signature_re.search(c_lambda).groups()
                sig = ",".join(sorted(self.arg_sep.split(sig)))
                new_lambda = "lambda %s: %s" % (sig, body)
                parsed.setdefault(sig, []).append(eval(new_lambda))
            return parsed

        raw_model = yaml.load(yaml_model)
        self.data = turn_values_to_list(flatten_inner(raw_model["data"]))
        self.priority = flatten_inner(raw_model.get("priority", {}))
        self.params = sorted(self.data.keys())
        self.constraints = Container()
        if raw_model.has_key("constraints"):
            for k in ["optional", "mandatory"]:
                setattr(self.constraints, k, _parse_constraints(raw_model["constraints"].get(k, {})))
        self.scheme = raw_model["scheme"]
        # if len(self.scheme.keys()) > 1:
        #     self.scheme = { "_1": self.scheme }

    def generate (self):
        slot_schemes = self.get_slot_schemes() # here we add complex params
        slots = MultiSlotScheme(*slot_schemes, generate=True, model=self)
        tests = run_alg(slots) # only complex constraints ????

    def get_slot_schemes (self):
        '''Returns list of slot schemes. Some of params of these slots are nested. Values for these params are added to hidded `_data` attribute during execution of this function.'''
        def reduce_inclusions (list_of_tups):
            l = len(list_of_tups)
            result = []
            for i in xrange(l):
                t1 = list_of_tups[i]
                add = True
                for j in xrange(i + 1, l):
                    t2 = list_of_tups[j]
                    if set(t1).issubset(set(t2)):
                        add = False
                        break
                if add: result.append(t1)
            return result

        def sort_by_size_by_lexi (list_of_tups):
            return sorted(list_of_tups,
                          lambda t1, t2: cmp(len(t1), len(t2)) or cmp(t1, t2))

        def norm_tuple (tup):
            return tuple(sorted(set(tup)))

        def recur_model (model):
            if isinstance(model, dict):
                valency = int(model.keys()[0][2:])
                params = model.values()[0] # list of submodels
                for i in xrange(len(params)):
                    params[i] = recur_model(params[i])
                result = []
                for tup_of_lists in it.combinations(params, valency):
                    result +=  map(lambda l: reduce(lambda res, t: res + t, l, tuple()), # sum (concat) tuples in list `l`
                                   it.product(*tup_of_lists))
                return result
            else:
                return [(model,)]
        return map(SlotScheme,
                   reduce_inclusions(
                       sort_by_size_by_lexi(
                           map(norm_tuple,
                               recur_model(self.scheme)))))
    
    def fits_optional_constraints (self, slot):
        return self._fits_constraints(slot, self.constraints.optional)

    def fits_mandatory_constraints (self, slot):
        return self._fits_constraints(slot, self.constraints.mandatory)

    def _fits_constraints (self, slot, constraints):
        slot_scheme = slot.slot_scheme
        scheme_set = set(slot_scheme)
        for sig, func_list in constraints.items():
            sig_list = sig.split(',')
            sig_set = set(sig_list)
            if sig_set.issubset(scheme_set):
                for func in func_list:
                    kwargs = {var: slot[var] for var in sig_list}
                    if not func(**kwargs):
                        return False
        return True
            
    def __getitem__ (self, item):
        return self.data[item]
