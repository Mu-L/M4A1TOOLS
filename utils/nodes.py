
def get_nodegroup_input_identifier(ng, name):
    item = ng.interface.items_tree.get(name, None)

    if item:

        return item.identifier, item.socket_type

    else:
        return None, None
