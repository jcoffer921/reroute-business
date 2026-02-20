from django.shortcuts import render


def wizard(request):
    return render(request, 'benefit_finder/wizard.html')
