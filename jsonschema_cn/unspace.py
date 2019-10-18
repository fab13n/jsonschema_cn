from parsimonious import NodeVisitor

class UnspaceVisitor(NodeVisitor):
    """Remove space tokens from a Parsimonious parse tree."""
    # TODO generate a set of space offsets in the code, so that they can
    # be compacted properly, including comments and excluding string contents.

    WHITESPACE_TOKEN = object()  # Sentinel value

    def visit__(self, node, children) -> object:
        """Replace whitspaces with an easy-to-filter sentinel value."""
        return self.WHITESPACE_TOKEN

    def generic_visit(self, node, children) -> tuple:
        """ The generic visit method. """
        node.children = [x for x in children if x is not self.WHITESPACE_TOKEN]
        return node
