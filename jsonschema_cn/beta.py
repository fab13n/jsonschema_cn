from . import tree as T

class BetaReductionVisitor(object):

    def __init__(self):
        self.definitions = None
        self.saved_definitions = []

    def visit_Schema_down(self, t: T.Schema) -> None:
        self.saved_definitions.append(self.definitions)
        if self.definitions is None:
            self.definitions = t.definitions
        else:
            merged_defs = {}
            merged_defs.update(self.definitions.values)
            merged_defs.update(t.definitions.values)
            self.definitions = T.Defitions(values=merged_defs)

    def visit_Schema_up(self, t: T.Schema) -> T.Schema:
        self.definitions = self.saved_definitions.pop()
        return T.Schema(value=t.value, definitions=T.Definitions(values={}))

    def visit_Reference_down(self, t: T.Reference) -> T.Type:
        try:
            definition = self.definitions.values[t.value]
        except KeyError:
            raise ValueError(f"Missing definition for {t.value}")
        return definition.visit(self)


def reduce(t: T.Schema) -> T.Schema:
    return t.visit(BetaReductionVisitor())
