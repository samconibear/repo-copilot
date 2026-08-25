; No method concept, fns never nest in structs, no containers entry.
; Name is 2 fields deep: function_definition -> declarator:
; function_declarator -> declarator: identifier.

(function_definition
  declarator: (function_declarator
    declarator: (identifier) @func.name)) @func.def

(struct_specifier
  name: (type_identifier) @class.name
  body: (field_declaration_list)) @class.def
