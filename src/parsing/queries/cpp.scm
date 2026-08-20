; Same declarator shape as C. Member fn name = field_identifier,
; top-level = identifier - hence (_) wildcard. containers =
; {"class_specifier": "name", "struct_specifier": "name"}.
; Known gap: out-of-line defs (Point::distance()) use
; qualified_identifier declarator, not resolved to parent (still
; captured as unattributed function via wildcard, not dropped).

(function_definition
  declarator: (function_declarator
    declarator: (_) @func.name)) @func.def

(class_specifier
  name: (type_identifier) @class.name
  body: (field_declaration_list)) @class.def

(struct_specifier
  name: (type_identifier) @class.name
  body: (field_declaration_list)) @class.def
