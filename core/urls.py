from django.contrib import admin
from django.urls import path, include  # Asegúrate de que 'include' esté aquí

urlpatterns = [
    path('admin/', admin.site.urls),

    # Añade esta línea:
    # Le dice a Django que cualquier URL que empiece con 'api/precios/'
    # debe ser manejada por las URLs que definimos en nuestra app.
    path('api/', include('gestion_precios.urls')),
]
