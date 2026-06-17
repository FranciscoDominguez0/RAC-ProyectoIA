# Usamos una imagen base de Ubuntu
FROM ubuntu:26.04

# Evitar interacciones durante la instalación de paquetes
ENV DEBIAN_FRONTEND=noninteractive

# 1, 2, 3: Actualizar sistema e instalar dependencias necesarias
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y git curl unzip python3 python3-pip python3-venv build-essential

# 4: Comprobación de versiones
RUN git --version && curl --version && pip3 --version

# 5, 6, 8: Crear directorio y establecerlo como directorio de trabajo
WORKDIR /var/www/ciberapp/RAC-ProyectoIA

# 7: En lugar de usar 'git clone', copiamos los archivos locales al contenedor
COPY . .

# 9: Crear el entorno virtual
ENV VIRTUAL_ENV=/var/www/ciberapp/RAC-ProyectoIA/venv
RUN python3 -m venv $VIRTUAL_ENV

# 10: "Activar" el entorno virtual añadiéndolo al PATH de Docker
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# 11, 12: Instalar dependencias de Python
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements.txt

# Exponer los puertos que utiliza Reflex (3000 para frontend y 8000 para backend)
EXPOSE 3000 8000

# Comando para iniciar la aplicación. 
# Nota: "nano .env" (Paso 13) no se ejecuta aquí. Docker usará el .env que ya configuraste localmente.
CMD ["reflex", "run"]
