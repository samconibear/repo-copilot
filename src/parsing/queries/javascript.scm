; Shared by javascript. typescript.scm = this + interface_declaration
; (not a node type in plain JS, fails to compile against it).

(function_declaration
  name: (identifier) @func.name) @func.def

(method_definition
  name: (property_identifier) @method.name) @method.def

(class_declaration
  name: (_) @class.name) @class.def

(variable_declarator
  name: (identifier) @arrow.name
  value: (arrow_function)) @arrow.def
