#SE ENCARGA DE MANEJAR LAS HERRAMIENTAS REQUERIDAS POR LAS RECETAS..
#..Y VALIDAR SUS RESULTADOS PARA DETERMINAR UN UNICO RESULTADO NG/OK

class VisionPipeline:
    def __init__(self, tool_registry: dict):
        """
        tool_registry = {
            "dmtx": DMTXTool(),
            ...
        }
        """
        #REGISTRAR HERRAMIENTAS PARA ACCEDER A ELLAS DESDE PIPELINE
        self.tool_registry = tool_registry

    def run(self, recipe: dict, contex: dict):
        results = {}            #DATA QUE VIENE DE CADA HERRAMIENTA
        overall_success = True  #VALIDACION GENERAL DETERMINANTE
        errors = []             #LISTA DE ERRORES ACUMULADOS DEL PROCESO DE CADA HERRAMIENTA
        contex.setdefault("outputs", {})
        contex.setdefault("debug_images", [])

        #RECABAR INFORMACION DE CADA RECETA GUARDADA {STEPS}
        for step in recipe["steps"]:
            tool_name = step["tool"]                #OBTENER EL NOMBRE DE LA HERRAMIENTA
            params = step.get("params", {})         #OBTENER LOS PARAMETROS DESIGNADOS PARA LA HERRAMIENTA
            required = step.get("required", True)   #FLAG DE REQUERIMIENTO

            tool = self.tool_registry.get(tool_name)    #PASAR INSTANCIA DE LA HERRAMIENTA ACTUAL A LA VARIABLE TOOL

            #CASO DE HERRAMIENTA NO ENCONTRADA
            if not tool:
                error_msg = f"Tool '{tool_name}' no encontrada" #MENSAJE DE ERROR
                errors.append(error_msg)    #ANEXAR MENSAJE DE ERROR A LA LISTA DE ERRORS
                if required:
                    print(f"[ERROR] Tool '{tool_name}' no encontrada")  #PRINT PARA LOG
                    return self._build_response(False, results, errors) #SALIR DE LA FUNCION Y LLAMAR A BUILD_RESPONSE
                continue

            print(f"[PIPELINE] Ejecutando {tool_name}") #LOD DE EJECUCION
            
            #M MERGE CONTEXT (DATOS, FUNCIONES, ETC.) + PARAMETROS DE HERRAMIENTA
            inputs = {**contex, **params}           

            result = tool.run(**inputs)     #EJECUTAR EL RUN DE TOOL_BASE DANDOLE TODA LA INFORMACION QUE A SU VEZ LLAMA A PROCESS DE LA HERRAMIENTA
            results[tool_name] = result     #ENLISTAR EL RESULTADO DE LA HERRAMIENTA EN UNA COLA

            print(f"[PIPELINE] Resultado: {result.data}")   #LOG DE PROCESO FINALIZADO

            #CASO DE RESULTADO NEGATIVO EN LA HERRAMIENTA
            if not result.success:
                overall_success = False     #CAMBIAR EL RESULTADO FINAL A NG - DETERMINANTE
                errors.append(result.error) #ANEXAR RAZON DE RESULTADO NEGATIVO

                if required:    #SI LA HERRAMIENTA ES REQUERIDA LLAMAR A BUILD_RESPONSE
                    print(f"[PIPELINE] Error en {tool_name}: {result.error}")   #LOG DEL ERROR
                    return self._build_response(False, results, errors)

            if result.data:
                contex["outputs"][tool_name] = result.data     #ACTUALIZAR CONTEXT CON LA DATA DE LA HERRAMIENTA PARA OTRAS HERRAMIENTAS

        return self._build_response(overall_success, results, errors)
    
    #FUNCION PARA MANEJAR EL RETURN A PIPELINE
    def _build_response(self, success, results, errors):
        #GARANTIZAR LA ESTRUCTURA BASE DE LOS DATOS EN EL RETURN
        return{
            "success": success,
            "results": results,
            "errors": errors
        }