; method_declaration is its own node type but NOT nested in struct -
; receiver is a field on the node itself. Resolved via receiver_owner
; (registry.py:_go_receiver_owner), not containers.

(function_declaration
  name: (identifier) @func.name) @func.def

(method_declaration
  name: (field_identifier) @method.name) @method.def

(type_spec
  name: (type_identifier) @class.name
  type: (struct_type)) @class.def
