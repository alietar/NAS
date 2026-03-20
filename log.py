from rich.console import Console
console = Console()

def info(msg):
    console.log("[blue bold]Info:[/] " + msg)

def success(msg):
    console.log("[green bold]Success:[/] " + msg)

def warning(msg):
    console.log("[yellow bold]Warning:[/] " + msg)

def error(msg):
    console.log("[red bold]Error:[/] " + msg)
    
def fatal_error(msg, exp):
    console.print("[bold red]Fatal Error:[/] " + msg + ", error is:")
    console.print(exp)

    console.print("\n[bold red]Quitting program")
    quit()