from . import tree as T

class BetaReductionVisitor(object):

    def visit_Schema_down(self, t: T.Schema) -> None:
        self.definitions = t.definitions

    def visit_Schema_up(self, t: T.Schema) -> T.Schema:
        return T.Schema(value=t.value, definitions=T.Definitions(values={}))

    def visit_Reference_down(self, t: T.Reference) -> T.Type:
        return self.definitions.values[t.value]


def reduce(t: T.Schema) -> T.Schema:
    return t.visit(BetaReductionVisitor())
