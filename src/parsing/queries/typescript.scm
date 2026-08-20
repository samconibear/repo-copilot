; = javascript.scm + interface_declaration. Same captures verified vs
; javascript for shared node types. Also used for tsx (superset grammar).

(function_declaration
  name: (identifier) @func.name) @func.def

(method_definition
  name: (property_identifier) @method.name) @method.def

(class_declaration
  name: (_) @class.name) @class.def

(variable_declarator
  name: (identifier) @arrow.name
  value: (arrow_function)) @arrow.def

(interface_declaration
  name: (type_identifier) @interface.name) @interface.def
