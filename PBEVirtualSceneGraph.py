


class PBEVirtualModelNode(PBEVirtualPandaNode):

    name = "ModelNode"
    type_index = bla.acquire_index()

    def __init__(self):
        super().__init__(self)
        self.preserve_transform = 0
        self.preserve_attributes = 0

    def write(self, encoder):
        super().write(encoder)
        encoder.add_uint8(self.preserve_transform)
        encoder.add_uint16(self.preserve_attributes)
