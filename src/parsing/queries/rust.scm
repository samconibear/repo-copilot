; No distinct method node type (like Python) - function_item nested in
; impl_item. containers = {"impl_item": "type"} (field is "type" not
; "name").

(function_item
  name: (identifier) @func.name) @func.def

(struct_item
  name: (type_identifier) @class.name) @class.def
