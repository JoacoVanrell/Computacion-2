import argparse
import json
from pathlib import Path

ARCHIVO = Path.home() / ".tareas.json"


def cargar_tareas():
    if ARCHIVO.exists():
        with open(ARCHIVO) as f:
            return json.load(f)
    return []


def guardar_tareas(tareas):
    with open(ARCHIVO, "w") as f:
        json.dump(tareas, f, indent=2, ensure_ascii=False)


def siguiente_id(tareas):
    if not tareas:
        return 1
    return max(t["id"] for t in tareas) + 1


def cmd_add(args):
    tareas = cargar_tareas()
    tarea = {
        "id": siguiente_id(tareas),
        "descripcion": args.descripcion,
        "prioridad": args.priority or "media",
        "hecha": False
    }
    tareas.append(tarea)
    guardar_tareas(tareas)
    prioridad_str = f" (prioridad: {tarea['prioridad']})" if args.priority else ""
    print(f"Tarea #{tarea['id']} agregada{prioridad_str}")


def cmd_list(args):
    tareas = cargar_tareas()

    # Filtros
    if args.pending:
        tareas = [t for t in tareas if not t["hecha"]]
    elif args.done:
        tareas = [t for t in tareas if t["hecha"]]
    if args.priority:
        tareas = [t for t in tareas if t["prioridad"] == args.priority]

    if not tareas:
        print("No hay tareas para mostrar.")
        return

    for t in tareas:
        estado = "x" if t["hecha"] else " "
        prioridad = f" [{t['prioridad'].upper()}]" if t["prioridad"] != "media" else ""
        print(f"#{t['id']} [{estado}] {t['descripcion']}{prioridad}")


def cmd_done(args):
    tareas = cargar_tareas()
    for t in tareas:
        if t["id"] == args.id:
            t["hecha"] = True
            guardar_tareas(tareas)
            print(f"Tarea #{args.id} completada")
            return
    print(f"Error: No existe la tarea #{args.id}")


def cmd_remove(args):
    tareas = cargar_tareas()
    for t in tareas:
        if t["id"] == args.id:
            respuesta = input(f'¿Eliminar "{t["descripcion"]}"? [s/N] ')
            if respuesta.lower() == "s":
                tareas.remove(t)
                guardar_tareas(tareas)
                print(f"Tarea #{args.id} eliminada")
            else:
                print("Cancelado.")
            return
    print(f"Error: No existe la tarea #{args.id}")


def main():
    parser = argparse.ArgumentParser(description="Gestor de tareas")
    subparsers = parser.add_subparsers(dest="comando")
    subparsers.required = True

    # Subcomando: add
    p_add = subparsers.add_parser("add", help="Agregar una tarea")
    p_add.add_argument("descripcion", help="Descripción de la tarea")
    p_add.add_argument("--priority", choices=["baja", "media", "alta"],
                       help="Prioridad de la tarea")

    # Subcomando: list
    p_list = subparsers.add_parser("list", help="Listar tareas")
    p_list.add_argument("--pending", action="store_true", help="Solo pendientes")
    p_list.add_argument("--done", action="store_true", help="Solo completadas")
    p_list.add_argument("--priority", choices=["baja", "media", "alta"],
                        help="Filtrar por prioridad")

    # Subcomando: done
    p_done = subparsers.add_parser("done", help="Marcar tarea como completada")
    p_done.add_argument("id", type=int, help="ID de la tarea")

    # Subcomando: remove
    p_remove = subparsers.add_parser("remove", help="Eliminar una tarea")
    p_remove.add_argument("id", type=int, help="ID de la tarea")

    args = parser.parse_args()

    comandos = {
        "add": cmd_add,
        "list": cmd_list,
        "done": cmd_done,
        "remove": cmd_remove
    }
    comandos[args.comando](args)


if __name__ == "__main__":
    main()