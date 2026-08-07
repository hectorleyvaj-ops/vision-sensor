#SE ENCARGA DE MANEJAR LAS HERRAMIENTAS REQUERIDAS POR LAS RECETAS..
#..Y VALIDAR SUS RESULTADOS PARA DETERMINAR UN UNICO RESULTADO NG/OK

from core.step_conditions import ConditionError, evaluate_condition

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
        execution_order = []
        skipped_steps = []
        overall_success = True  #VALIDACION GENERAL DETERMINANTE
        errors = []             #LISTA DE ERRORES ACUMULADOS DEL PROCESO DE CADA HERRAMIENTA
        contex.setdefault("outputs", {})
        contex.setdefault("outputs_by_tool", {})
        contex.setdefault("debug_images", [])

        steps = recipe.get("steps", []) if isinstance(recipe, dict) else []
        if not steps:
            return self._build_response(
                False,
                results,
                ["La receta no contiene herramientas ejecutables"],
                execution_order,
                skipped_steps,
            )

        #RECABAR INFORMACION DE CADA RECETA GUARDADA {STEPS}
        for index, step in enumerate(steps):
            tool_name = step["tool"]                #OBTENER EL NOMBRE DE LA HERRAMIENTA
            step_id = step.get("id") or f"{tool_name}_{index + 1}"
            params = step.get("params", {})         #OBTENER LOS PARAMETROS DESIGNADOS PARA LA HERRAMIENTA
            required = step.get("required", params.get("required", True))   #FLAG DE REQUERIMIENTO

            if not step.get("enabled", True):
                skipped_steps.append(step_id)
                continue

            try:
                should_run = evaluate_condition(
                    step.get("condition"),
                    results,
                    contex,
                )
            except ConditionError as exc:
                errors.append(f"Condicion invalida en {step_id}: {exc}")
                return self._build_response(
                    False,
                    results,
                    errors,
                    execution_order,
                    skipped_steps,
                )

            if not should_run:
                skipped_steps.append(step_id)
                continue

            if step_id in results:
                error_msg = f"Step id duplicado durante ejecucion: {step_id}"
                errors.append(error_msg)
                return self._build_response(
                    False, results, errors, execution_order, skipped_steps
                )

            tool = self.tool_registry.get(tool_name)    #PASAR INSTANCIA DE LA HERRAMIENTA ACTUAL A LA VARIABLE TOOL

            #CASO DE HERRAMIENTA NO ENCONTRADA
            if not tool:
                error_msg = f"Tool '{tool_name}' no encontrada" #MENSAJE DE ERROR
                errors.append(error_msg)    #ANEXAR MENSAJE DE ERROR A LA LISTA DE ERRORS
                if required:
                    print(f"[ERROR] Tool '{tool_name}' no encontrada")  #PRINT PARA LOG
                    return self._build_response(
                        False, results, errors, execution_order, skipped_steps
                    ) #SALIR DE LA FUNCION Y LLAMAR A BUILD_RESPONSE
                skipped_steps.append(step_id)
                continue

            print(f"[PIPELINE] Ejecutando {step_id} ({tool_name})") #LOD DE EJECUCION

            #M MERGE CONTEXT (DATOS, FUNCIONES, ETC.) + PARAMETROS DE HERRAMIENTA
            inputs = {**contex, **params}

            result = tool.run(**inputs)     #EJECUTAR EL RUN DE TOOL_BASE DANDOLE TODA LA INFORMACION QUE A SU VEZ LLAMA A PROCESS DE LA HERRAMIENTA
            results[step_id] = result
            execution_order.append(step_id)

            print(f"[PIPELINE] Resultado: {result.data}")   #LOG DE PROCESO FINALIZADO

            #CASO DE RESULTADO NEGATIVO EN LA HERRAMIENTA
            if not result.success:
                errors.append(result.error) #ANEXAR RAZON DE RESULTADO NEGATIVO

                if required:    #SI LA HERRAMIENTA ES REQUERIDA LLAMAR A BUILD_RESPONSE
                    print(f"[PIPELINE] Error en {step_id}: {result.error}")   #LOG DEL ERROR
                    return self._build_response(
                        False, results, errors, execution_order, skipped_steps
                    )

            if result.data:
                contex["outputs"][step_id] = result.data
                contex["outputs_by_tool"].setdefault(tool_name, []).append(result.data)

        if not execution_order:
            errors.append("Ninguna herramienta cumplio su condicion de ejecucion")
            overall_success = False

        return self._build_response(
            overall_success,
            results,
            errors,
            execution_order,
            skipped_steps,
        )

    #FUNCION PARA MANEJAR EL RETURN A PIPELINE
    def _build_response(
        self,
        success,
        results,
        errors,
        execution_order,
        skipped_steps,
    ):
        #GARANTIZAR LA ESTRUCTURA BASE DE LOS DATOS EN EL RETURN
        return{
            "success": success,
            "results": results,
            "errors": errors,
            "execution_order": execution_order,
            "skipped_steps": skipped_steps,
        }
