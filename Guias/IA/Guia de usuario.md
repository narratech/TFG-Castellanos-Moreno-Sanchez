# **GUIA DE USUARIO HERRAMIENTA**

---

# **Índice**
1. [**Entrenamiento del modelo GRU de emociones**](#1-GRU)  
   1.1 [Instalación](#11-instalacion)  
   1.2 [Instrucciones](#12-instrucciones)  
   
2. [**Guía de instalación plugin**](#2-plugin)  
   2.1 [Preparación del entorno y navegación](#21-entorno)  
   2.2 [El personaje base (NPC)](#22-NPC)  
   2.3 [Configuración del Cerebro (Comoponente EmotionAI)](#23-componente)  
   2.4 [Conexión con el sistema de animación](#24-sistema)  
   2.5 [Generación de acciones en el entorno](#25-acciones)  
   2.6 [Reacciones y árboles de estado (StateTrees)](#26-statetrees)  
   
5. [**Ampliación de información**](#3-info)

---
<div style="page-break-before: always;"></div>

# **1. Entrenamiento del modelo GRU de emociones**  
<a name="1-GRU"></a>

## **1.1 Instalación**  
<a name="11-instalacion"></a>
Es necesario tener instalado [Python](https://www.python.org/downloads/release/python-3144/).
  1. Descargar el comprimido de GitHub y extraerlo en una carpeta vacía.
  2. Accede a la ruta TFG-Castellanos-Sanchez\GRU y ejecuta el archivo import_dependencies.bat para generar el entorno virtual en la carpeta venv.
  3. Copiar tu dataset en formato csv separado con comas dentro de la carpeta dataset.

## **1.2 Instrucciones**  
<a name="12-instrucciones"></a>
Una vez instalado y generado el entorno de python en la carpeta venv. 
Permanenciendo en la ruta Castellanos-Moreno-Sanchez\GRU, abriremos el archivo config.ini y rellenaremos la sección Dataset.

Podremos entrenar nuestro modelo haciendo uso de una autoencoder para aumentar el dataset o entrenarlo directamente. Ya hay una configuración por defecto para entrenar el autoencoder y el modelo pero se puede modificar en caso de que se quiera ajustar dentro de las secciones Autoencoder y GRU en config.ini.

Si se quiere entrenar el modelo ejecutaremos [gru_only.bat](#gru).
Si se quiere entrenar el modelo aplicando antes el autoencoder ejecutaremos [training.bat](training).

En ambos casos también aplicará onehot a las entradas en las columnas categóricas.

Si, además, se quiere comprobar el entrenamiento con nuevos datos de prueba. Añadir dichos datos en un archivo realset.csv dentro de la carpeta dataset y ejecutar [testeo.bat](testeo) después de haber generado el modelo.
A continuación, con el modelo ya dentro de la carpeta models pasaremos a unreal engine

---

# **2. Guía de instalación plugin**  
<a name="2-plugin"></a>
Guardaremos el modelo generado dentro de la carpeta Content de nuestro proyecto de Unreal.

## **2.1 Preparación del entorno y navegación**  
<a name="21-entorno"></a>
Para que la IA funcione correctamente, el entorno debe estar adaptado a las acciones con las que fue entrenada.
*	Crea un nivel nuevo o utiliza un entorno existente. Como punto de partida, la herramienta incluye un nivel de ejemplo ya preconfigurado llamado Demo2, situado en Content/TFG-Castellanos-Sanchez/Levels
*	Fundamental para el movimiento: Para que el NPC pueda desplazarse (patrullar, huir, etc.), es obligatorio añadir un volumen de navegación a la escena. Busca en el panel de Place Actors el elemento NavMesh Bounds Volume, arrástralo a tu nivel y escala el volumen para que cubra todo el suelo.

## **2.2 El personaje base (NPC)**  
<a name="22-NPC"></a>
La herramienta proporciona un actor preconfigurado listo para usar.
*	Navega a la ruta Content/TFG_CastellanosSanchez/Blueprints/Npc y arrastra al nivel el actor llamado DemoSandBoxCharacter_Mover.
*	Nota sobre personalización: Este actor viene por defecto con un MetaHuman y componentes de ejemplo asignados. Su propósito es servir como plantilla base. El usuario puede (y debe) personalizarlo vaciando las acciones predeterminadas e insertando su propio MetaHuman (modificando el Skeletal Mesh en el VisualOverride) para adaptarlo a las necesidades estéticas de su proyecto.
   - Para crear tu propio metahuman sigue los pasos del siguiente video acerca de [Metahuman Creator](https://youtu.be/2M22x-Jm4WE). La otra opción es usar alguno de los que vienen en el zip del Content que te tuviste que descargar. 
   - Una vez creado el metahuman, accederás al componente Visual Override del actor DemoSandBoxCharacter_Mover, buscarás el parametro de Child Actor y agregarás el blueprint del metahuman que creaste. 

## **2.3 Configuración del Cerebro (Comoponente EmotionAI)**  
<a name="23-componente"></a>
Ahora dotaremos al NPC de la capacidad de procesar las emociones.
A continuación, añadiremos a nuestro NPC el componente EmocionIA. Ubicado en source del proyecto de Unreal.
En este componente tendremos que rellenar algunos campos dentro del editor.

Pondremos dentro del campo Model Path la ruta de nuestro modelo y el numbre del archivo partiendo como raíz la carpeta Content de nuestro proyecto de unreal.

![Config](Imagenes/Guia_UE_1.png)

Antes de pasar a la siguiente parte queremos que sepas que hay un Actor Blueprint de los siguientes pasos donde ya hay una configuración acerca de un ejemplo ya montado para que te sirva de ayuda, el cuál, se encuentra en Content/TFG-Castellanos-Sanchez/IA, y se llama Test_EmotionIA. Por lo tanto, una vez configurado el componente puedes hacer inferencias con el modelo entrenado con el nodo Run Inference dentro del Event Graph.

Requerirá como parámetro un vector de floats con todos los parámetros de la nueva entrada. La salida será un vector de floats con las salidas en el mismo orden que se puso en el archivo config.ini en el parámetro OUTPUT_NAMES.

![Codigo1](Imagenes/Guia_UE_5.png)

Para convertir valores categóricos, se puede usar el nodo One Hot Encode with Categories. Que tendrá como parámetros el string a codificar y un array de strings con todos los posibles valores que puede tener el valor.

![Codigo2](Imagenes/Guia_UE_4.png)

El formato esperado del parámetro de Run Inference tendrá primero todos los valores discretos y luego todos los categóricos según el orden en el que aparecen en el dataset con el que entrenó.
Ej:
(Dataset) DiscretoA, DiscretoB, CategoricoA, DiscretoC, CategoricoB -> (Run Inference) DiscretoA, DiscretoB, DiscretoC, CategoricoA_1, …,  CategoricoA_X, CategoricoB_1, …, CategoricoB_X.

## **2.4 Conexión con el sistema de animación**  
<a name="24-sistema"></a>

Para que las emociones calculadas por la IA deformen físicamente al personaje, necesitamos el gestor de animación.
*	Navega a la ruta Content/TFG_CastellanosSanchez/Blueprints/ExpresionFacial y arrastra al nivel el actor BP_AnimationSystem.
*	Selecciona el BP_AnimationSystem en tu nivel y, en el panel de Detalles, localiza la variable Metahuman Actor. Asígnale usando el cuentagotas el NPC (DemoSandBoxCharacter_Mover) que pusiste en el Paso 2.
*	Activa la casilla de la variable Use Emotion. Esto habilitará la comunicación en tiempo real para que los cambios emocionales se reflejen físicamente en el NPC.
*	Para terminar de conectar el modelo con el sistema de animación, accederemos al componente al blueprint o parte del código creado en el paso 2.3, y tendremos que enviar el mapa de emociones que saca el modelo al actor de BP_AnimationSystem. Para ello podemos hacer algo parecido a la siguiente imagen:

![Codigo3](Imagenes/SetEmotions.png)

Donde Animation Actor es una variable de tipo actor que hace referencia al BP_AnimationSystem. 

## **2.5 Generación de acciones en el entorno**  
<a name="25-acciones"></a>

El comportamiento de la IA depende de los estímulos externos.
*	El usuario debe programar en su nivel las acciones y eventos (variables de entorno) coherentes con el dataset con el que entrenó a la IA.
*	Nuestra demo incluye ejemplos de interacción ya configurados que alteran estos estados, tales como la aparición de lluvia o la acción del jugador de equipar un arma e intentar golpear al NPC.

## **2.6 Reacciones y árboles de estado (StateTrees)**  
<a name="26-statetrees"></a>

Finalmente, el NPC debe traducir esas emociones en comportamientos de IA.
*	Asegúrate de que tu NPC está poseído por el controlador de IA proporcionado: AIC_NPC_Demo.
*	A este controlador se le debe pasar por parámetro un State Tree (Árbol de Estados), que el usuario diseñará para dictar cómo reacciona el NPC ante las diferentes acciones del entorno. Para este paso también proporcionamos un ejemplo de uso de un State Tree que puedes encontrar en Content/TFG_CastellanosSanchez/Blueprints/AI/StateTree llamado ST_NPC_Principal
*	Plantilla disponible: Proporcionamos un State Tree a modo de plantilla que incluye estados lógicos fundamentales (Sentirse amenazado, Caminar, Correr). Recomendamos a los usuarios utilizar este árbol como un Linked Asset (Sub-árbol) dentro de sus propios State Trees principales para agilizar el desarrollo de reacciones complejas.

---

# **3. Ampliación de información**   
<a name="3-info"></a>
Dentro del archivo config.ini hay varios elementos que el desarrollador puede modificar para ajustar el modelo:

**Dataset (obligatorio):**  
  *	CSV_NAME: nombre del archivo csv con el dataset para entrenar el modelo.

  *	TESTER_CSV_NAME: nombre del archivo csv con el dataset para comprobar el modelo (se recomienda que los datos sean distintos a los de CSV_NAME).

  *	OUTPUT_NAMES: nombre de las columnas con las emociones que se quiere que el modelo prediga.

  *	SEQUENCE_LENGTH: longitud de la secuenca de entradas con la que el modelo GRU va a ser entrenado.

  *	BLOCK_SIZE: Tamaño de las entradas contiguas dentro del dataset.

[Imagen]

**Autoencoder:**  
  *	N_SYNTHETIC: Número de secuencias sintéticas a generar por el autoencoder.

  *	EPOCHS: Número iteraciones que hará durante el entrenamiento del autoencoder.

  *	LATENT_SIZE: Tamaño de las capas latentes del autoencoder.

  *	HIDDEN_SIZE: Tamaño de las capas ocultas del autoencoder

  *	HIDDEN_NUM: Número de capas ocultas del autoencoder

  *	LEARNING_RATE: Tasa de aprendizaje del autoencoder.

  *	BETA_VAE: valor de beta que usa el autoencoder.

  *	BATCH_SIZE: Tamaño del batch del autoencoder.

  *	USE_CUDA: Indica si usara la GPU (True) o la CPU (False).

**GRU:**  
  *	EPOCHS: Número iteraciones que hará durante el entrenamiento del GRU.

  *	HIDDEN_SIZE: Tamaño de las capas ocultas del modelo GRU

  *	NUM_LAYERS: Número de capas ocultas del GRU.

  *	BATCH_SIZE: Tamaño del batch del modelo GRU.

  *	LEARNING_RATE: Tasa de aprendizaje del GRU.

  *	ACCURACY_THRESHOLD: Rango para dar por valido los valores de la salida

  *	USE_CUDA: Indica si usara la GPU (True) o la CPU (False).

**TRAINING.BAT**  
<a name="training"></a>
Genera casos de prueba sintéticos a partir del dataset proporcionado en la carpeta dataset. Se aplica de manera automática one-hot sobre las columnas de entrada categoricas

Los datos sintéticos se guardaran en la misma carpeta con el nombre de “generated_{nombre del archivo dataset}”.

Al terminar de generar los nuevos datos mostrará por pantalla la distribución de estos en formato de gráfico de puntos.

También aplicará el entrenamiento del modelo GRU con los datos generados por el autoencoder y exportará en la carpeta models lo necesario para exportar tu modelo a Unreal Engine (gru_model.onnx y gru_model.onnx.data) y un archivo gru_model.pth para poder realizar testeos.

**GRU_ONEHOT.BAT**  
<a name="gru"></a>
Entrena el modelo dentro de dataset aplicando one-hot a las columnas de entrada categóricas.

Al finalizar el entrenamiento, por consola se dará información sobre las matrices de confusión de las salidas y la precisión del modelo respecto al dataset.


**TESTEO.BAT**  
<a name="testeo"></a>
Comprueba tu modelo gru_model.pth ya exportado en la carpeta models con un dataset nuevo dentro de la carpeta dataset.

Al terminar las predicciones se mostrará por pantalla la correlación entre las salidas del dataset y las predichas por el modelo ya entrenado.

