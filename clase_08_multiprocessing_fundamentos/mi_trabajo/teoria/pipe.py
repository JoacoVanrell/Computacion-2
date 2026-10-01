import multiprocessing

def hijo(conn):
    conn.send("Hola padre")
    print(f"Hijo recibió: {conn.recv()}")
    conn.close()

if __name__ == "__main__":
    padre_conn, hijo_conn = multiprocessing.Pipe()

    p = multiprocessing.Process(target=hijo, args=(hijo_conn,))
    p.start()

    print(f"Padre recibió: {padre_conn.recv()}")
    padre_conn.send("Hola hijo")
    p.join()