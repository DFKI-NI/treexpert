from django.shortcuts import redirect


def redirect_to_docs(request):
    return redirect("/api/docs")
