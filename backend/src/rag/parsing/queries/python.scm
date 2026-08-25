; No distinct method node type. func->method resolved in engine.py via
; LanguageConfig.containers = {"class_definition": "name"} in
; registry.py, not a separate capture here.

(function_definition
  name: (identifier) @func.name) @func.def

(class_definition
  name: (identifier) @class.name) @class.def
