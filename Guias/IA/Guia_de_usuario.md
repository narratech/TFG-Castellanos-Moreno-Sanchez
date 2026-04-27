# GUÍA DE USUARIO
> **Documentación Técnica Integrada**
> Guía completa para el entrenamiento del modelo GRU de emociones y su posterior integración mediante plugin en Unreal Engine.

---

## Índice de Contenidos

1. [**Entrenamiento del modelo GRU de emociones**](#1-entrenamiento-del-modelo-gru-de-emociones)
   * 1.1 [Requisitos e Instalación](#11-requisitos-e-instalación)
   * 1.2 [Instrucciones de Uso](#12-instrucciones-de-uso)
2. [**Guía de instalación del Plugin en Unreal Engine**](#2-guía-de-instalación-del-plugin-en-unreal-engine)
   * 2.1 [Preparación del entorno y navegación](#21-preparación-del-entorno-y-navegación)
   * 2.2 [El personaje base (NPC)](#22-el-personaje-base-npc)
   * 2.3 [Configuración del Cerebro (Componente EmotionAI)](#23-configuración-del-cerebro-componente-emotionai)
   * 2.4 [Conexión con el Cerebro (Componente `BPC_PsicologyNPC`)](#24-conexion-con-el-cerebro)
   * 2.5 [Conexión con el sistema de animación](#25-conexión-con-el-sistema-de-animación)
   * 2.6 [Interacción y Control del Entorno (Variables Dinámicas)](#26-interaccion-control-del-entorno)
   * 2.7 [Arquitectura de Comportamiento: StateTrees y Animaciones](#27-reacciones-y-árboles-de-estado-statetrees)
3. [**Ampliación de Información y Referencia Técnica**](#3-ampliación-de-información-y-referencia-técnica)
   * 3.1 [Configuración de parámetros (`config.ini`)](#31-configuración-de-parámetros-configini)
   * 3.2 [Referencia de Scripts de Ejecución](#32-referencia-de-scripts-de-ejecución)

---

<div style="page-break-before: always;"></div>

# 1. Entrenamiento del modelo GRU de emociones <a name="1-entrenamiento-del-modelo-gru-de-emociones"></a>

## 1.1 Requisitos e Instalación <a name="11-requisitos-e-instalación"></a>

Para inicializar el entorno de entrenamiento, es requisito indispensable tener instalado [Python](https://www.python.org/downloads/release/python-3144/).

**Pasos de instalación:**
> [!IMPORTANT]
> (`poner enlace mas adelante del archivo comprimido`)
1. Descargar el archivo comprimido del repositorio de GitHub y extraer su contenido en un directorio vacío.
2. Navegar a la ruta `TFG-Castellanos-Sanchez\GRU` y ejecutar el script `import_dependencies.bat`. Este proceso generará automáticamente un entorno virtual dentro de la carpeta `venv`.
3. Copiar el dataset propio (en formato `.csv` delimitado por comas) dentro del directorio `dataset`.

## 1.2 Instrucciones de Uso <a name="12-instrucciones-de-uso"></a>

Una vez completada la instalación y generado el entorno virtual, proceda con los siguientes pasos desde el directorio `Castellanos-Sanchez\GRU`:

1. Abra el archivo de configuración `config.ini`.
2. Cumplimente los datos requeridos en la sección **`[Dataset]`**.
> [!IMPORTANT]
> (Explicar algo mejor por si no se entiende lo de cumplimentar los datos requeridos)

El sistema permite dos modalidades de entrenamiento:
* **Entrenamiento Directo:** Ejecutando `gru_only.bat`.
* **Entrenamiento con Autoencoder (Aumento de datos):** Ejecutando `training.bat`. *(Existe una configuración por defecto en las secciones `[Autoencoder]` y `[GRU]` del `config.ini` que puede ser modificada según las necesidades del proyecto).*

> **Nota:** En ambas modalidades, el sistema aplicará automáticamente la codificación *One-Hot* a las entradas correspondientes a las columnas categóricas.

### Pruebas y Validación (Testeo)
Si desea validar el entrenamiento con nuevos datos empíricos:
1. Añada los nuevos datos en un archivo llamado `realset.csv` dentro del directorio `dataset`.
2. Ejecute el script `testeo.bat` (requiere haber generado previamente el modelo).
3. Tras la validación, el modelo generado se ubicará en la carpeta `models`, quedando listo para su integración en Unreal Engine.

---

# 2. Guía de instalación del Plugin en Unreal Engine <a name="2-guía-de-instalación-del-plugin-en-unreal-engine"></a>

> **Nota de Diseño:** Para facilitar las pruebas y la integración, esta guía se apoya en los sistemas preconstruidos utilizados en nuestra **Demo1**. En lugar de programar la lógica desde cero, le guiaremos para implementar nuestras herramientas modulares. De esta forma, obtendrá una IA funcional de forma casi inmediata, comprendiendo en cada paso el funcionamiento interno del sistema.

**Paso previo:** Copie el modelo generado (ubicado en la carpeta `models`) dentro del directorio `Content` de su proyecto de Unreal Engine.

## 2.1 Preparación del entorno y navegación <a name="21-preparación-del-entorno-y-navegación"></a>

Para garantizar el correcto funcionamiento de la Inteligencia Artificial, el entorno debe soportar las acciones parametrizadas durante el entrenamiento.

* **Nivel de trabajo:** Puede crear un nivel nuevo o utilizar uno existente. Recomendamos encarecidamente utilizar el nivel preconfigurado de prueba: `Demo2`, localizado en `Content/TFG-Castellanos-Sanchez/Levels`. De esta forma será más rápido llegar a nuestro objetivo de crear un nivel parecido al de la Demo1
* **Volumen de Navegación:** Es estrictamente necesario añadir un volumen de navegación para permitir el desplazamiento del NPC (patrullaje, huida, etc.). Desde el panel *Place Actors*, arrastre un `NavMesh Bounds Volume` a la escena y escálelo hasta cubrir toda la superficie transitable. Pulsando la tecla **P** podrá visualizar en verde las zonas navegables.

## 2.2 El personaje base (NPC) <a name="22-el-personaje-base-npc"></a>

Se proporciona un actor preconfigurado (`DemoSandBoxCharacter_Mover`) ubicado en `Content/TFG_CastellanosSanchez/Blueprints/Npc`. Arrástrelo al nivel.

> **Personalización del NPC (MetaHuman)**
> Por defecto, el actor integra un MetaHuman y componentes de prueba. Debe personalizarlo asignando su propio MetaHuman modificando el *Skeletal Mesh* en el componente `VisualOverride`.
> 1. Para crear un modelo personalizado, consulte el [Video tutorial de MetaHuman Creator](https://youtu.be/2M22x-Jm4WE) (o utilice los modelos incluidos en el `.zip` de la carpeta Content/Metahuman).
> 2. Acceda al componente `Visual Override` del actor, localice el parámetro `Child Actor` y asigne el Blueprint de su MetaHuman.

## 2.3 Configuración del Cerebro (Componente EmotionAI) <a name="23-configuración-del-cerebro-componente-emotionai"></a>

> [!IMPORTANT]
> Revisar todo este apartado para adaptarlo para que en vez de que use directamente nuestro Test_EmotionIA, tengamos un blueprint donde tenga que ir metiendo o uniendo los nodos pero que en todo momento se le explique que hace para que entienda como funciona. Además debemos puntializar que en nuestra version hemos puesto variables para personalidad que deben instanciar en el editor, estaria bien darles algun ejemplo de personalidades a poner con una tabla o algo y explicarles rasgos de cada personalidad

Para dotar al NPC de procesamiento emocional, añada el componente **`EmotionIA`** al Blueprint del personaje (ubicado en el `source` del proyecto). *Importante: Aplíquelo en el Blueprint, no como instancia en el nivel.*

En el panel de detalles del componente:
* Defina en **`Model Path`** la ruta y nombre del archivo de su modelo, utilizando la carpeta `Content` como raíz.

![Configuración del Modelo](Imagenes/Guia_UE_1.png)

### Inferencias desde Blueprints
Dispone de un Actor Blueprint de ejemplo ya configurado en `Content/TFG-Castellanos-Sanchez/IA` llamado `Test_EmotionIA`. 
Utilice el nodo **`Run Inference`** dentro del Event Graph para realizar predicciones.

* **Entrada:** Un vector de floats (`Array<float>`) con los parámetros de entrada.
* **Salida:** Un diccionario de clave string y valor float con los nombres según el parámetro `OUTPUT_NAMES` del `config.ini`.

![Nodo Run Inference](Imagenes/Guia_UE_5.png)

Para la conversión de valores categóricos, utilice el nodo **`One Hot Encode with Categories`** pasando como parámetros el *string* a codificar y un array con los valores posibles.

![Nodo One Hot Encode](Imagenes/Guia_UE_4.png)

> **Formato de los datos para la Inferencia:**
> El vector debe contener primero los valores continuos/discretos y posteriormente los categóricos, respetando el orden del dataset.
> *Ejemplo:* > `[DiscretoA, DiscretoB, CategoricoA, DiscretoC, CategoricoB]` **➜** `[DiscretoA, DiscretoB, DiscretoC, CategoricoA_1...CategoricoA_X, CategoricoB_1...CategoricoB_X]`

## 2.4 Conexión con el Cerebro (Componente `BPC_PsicologyNPC`) <a name="24-conexion-con-el-cerebro"></a>

> **Recomendación de Diseño (Acelerador de Integración):** > En lugar de programar la memoria y los sensores de cada NPC desde cero, le sugerimos encarecidamente utilizar nuestro componente modular **`BPC_PsicologyNPC`**. Este componente actúa como la "corteza prefrontal" del personaje: gestiona sus recuerdos, evalúa el entorno periódicamente y procesa quién golpea a quién, enviando los datos limpios al modelo GRU. Es un requerimiento clave para que los comportamientos avanzados de la demo funcionen sin configuraciones extra.

Para implementarlo, simplemente abra el Blueprint de su personaje (ej. `DemoSandBoxCharacter_Mover`), haga clic en *Add Component* y añada **`BPC_PsicologyNPC`**.

### 2.4.1 Variables Expuestas (Configuración en Editor)
Una vez añadido el componente, selecciónelo para ver su panel de Detalles. Encontrará una serie de variables públicas que debe configurar directamente en el editor del nivel para cada NPC instanciado:

> [!IMPORTANT]
> Aclarar que algunas variables todavia no puede ser metidas pq se iran expplicando más adelante

* **Categoría *Predeterminado***
  * **`Test Emotio AI`:** Referencia directa al actor `Test_EmotionIA` de la escena, el cual contiene la red neuronal GRU encargada de calcular la inferencia.
* **Categoría *Patrol Point***
  * **`Actor To Follow`:** El actor o punto de ruta inicial hacia el que el NPC debe dirigirse al empezar la simulación. Más adelante se explicará que se debe instanciar aquí.
  * **`Escape Patrol Point` (Array):** Una lista de *Target Points* distribuidos por el mapa que el NPC utilizará como refugios aleatorios cuando el GRU detecte un nivel alto de miedo. Al igual que antes más adelante se explicará como instanciar dichos puntos. 
  * **`Fire Patrol Point`:** Una ubicación segura predefinida relacionada con el clima (por ejemplo, una chimenea) a la que el NPC acudirá si la temperatura es desfavorable. Lo mismo que con las dos anteriores variables. 
* **Categoría *Social***
  * **`Social Memory` (Diccionario / Map):** ¡Vital para la interacción! Es un mapa que relaciona *Actores* reales del nivel con nuestro *Enum* `E_SocialRole` (Ej: El jugador = "Jugador", Otro NPC = "NPC1"). El componente utiliza esta memoria para saber a quién está viendo. En este caso no hará falta hacer nada ya que al iniciar el nivel se instancian los valores según el rol escogido al jugar. 
* **Categoría *Entorno***
  * **`Range`:** El radio de visión y consciencia del NPC (en unidades de Unreal).

### 2.4.2 Funcionamiento Interno (¿Qué hace este componente por usted?)

Si decide investigar el Blueprint por dentro, verá que hemos optimizado la arquitectura siguiendo estándares de la industria AAA:

**1. Optimización del Rendimiento (Behavior Tick)**
En lugar de saturar la CPU evaluando distancias en cada fotograma (`Event Tick`), el componente inicializa un **Timer** en el `Begin Play` que se ejecuta cada 0.3 segundos (`ServerBehaviourTick`). Solo si el NPC puede actuar (`CanTakeAction`), procederá a recalcular las distancias a otros NPCs y evaluar a su objetivo actual. Esto permite tener múltiples NPCs en pantalla manteniendo un rendimiento óptimo.

**2. Sistema de Memoria de Navegación (`SetActorToFollow`)**
Cuenta con una lógica robusta para interrumpir rutas. Cuando surge una emergencia (ej. huir de un disparo), el evento `SetActorToFollow` recibe el nuevo punto de escape, pero permite guardar el destino original en la variable **`Old Actor To Follow`**. Cuando la emergencia termina, el NPC recuperará este dato y continuará su rutina exactamente por donde la dejó.

**3. Testigo de Combate y Roles Sociales (`OnWitnessAttack`)**
Es el sistema más avanzado del componente. Si ocurre una pelea en el radio de visión del NPC, este evento recibe quién es el Agresor y quién es la Víctima. 
El código busca a estos actores dentro de su **`Social Memory`** (el diccionario que usted configuró). Al identificar sus roles (por ejemplo, si descubre que la víctima es "Yo" o es un "Aliado"), mapea inmediatamente estos roles en las variables `Rol Agresor` y `Rol Victima` y dispara una actualización directa al Cerebro Emocional (`Set Roles Emotion AI`). El modelo GRU procesará este evento al instante, alterando drásticamente el estado emocional del NPC hacia el miedo o la ira.

## 2.5 Conexión con el sistema de animación <a name="25-conexión-con-el-sistema-de-animación"></a>

Para reflejar físicamente las emociones procesadas:

1. Navegue a `Content/TFG_CastellanosSanchez/Blueprints/ExpresionFacial` e inserte el actor **`BP_AnimationSystem`** en el nivel.
2. Seleccione el actor, busque la variable **`Metahuman Actor`** en Detalles y asigne el NPC creado en el paso 2.2 mediante el cuentagotas.
3. Active la variable **`Use Emotion`** para habilitar la deformación facial en tiempo real.
4. Envíe el mapa de emociones (salida del nodo `Run Inference` del paso 2.3) al actor `BP_AnimationSystem`. A continuación se muestra un ejemplo de implementación:

![Set Emotions](Imagenes/SetEmotions.png)
*(Donde `Animation Actor` es una referencia a la instancia de `BP_AnimationSystem`)*.

## 2.6 Interacción y Control del Entorno (Variables Dinámicas) <a name="26-interaccion-control-del-entorno"></a>

La IA reacciona dinámicamente a los estímulos. Para facilitar las pruebas, hemos incluido sistemas preconfigurados que actúan como "disparadores" para las emociones del NPC:

### Gestor Climático (`BP_WeatherManager`)

Este Blueprint global controla el clima del nivel. Arrástrelo a su escena.
* **¿Qué hace?** Modifica visualmente el entorno (nubes, lluvia, iluminación) y sirve de referencia global para todos los NPCs.
* **Variables Clave:**
  * Particle System: es neceario agregarle el particle system de la lluvia llamado `Rain`.
  * `Esta Lloviendo` (Booleano): Al activarse, los Evaluadores de la IA detectan el cambio de clima y el GRU ajusta las emociones, obligando al NPC a buscar refugio o calentarse.
  * Dispone de líneas de tiempo (Timelines) internas para controlar la intensidad de la precipitación.

### Objetos Interactuables (Ej. El Arma / Pistola)
> [!IMPORTANT]
> Revisar si en la demo 2 la pistola ya esta, sino hay que indicarle que la debe mover al nivel 

Dentro de la demo encontrará objetos interactuables diseñados para alterar el comportamiento del NPC.
* **Uso del Arma:** El jugador puede interactuar con el arma (pulsando la tecla `E` para recogerla/equiparla). Al hacer clic, el arma apuntará.
* **Impacto en la IA:** El NPC cuenta con conos de visión. Si el jugador entra en su campo de visión con el arma equipada, el estado de amenaza (`IsReaction`) se vuelve verdadero. El modelo GRU procesará un aumento drástico del miedo, lo que obligará al NPC a interrumpir sus tareas y huir al punto de escape más lejano.


## 2.7 Arquitectura de Comportamiento: StateTrees y Animaciones <a name="27-reacciones-y-árboles-de-estado-statetrees"></a>

El puente entre las emociones predichas por el GRU y las acciones físicas del personaje se gestiona mediante un **State Tree**. 

Asigne el controlador de IA proporcionado (**`AIC_NPC_Demo`**) a su NPC. Este controlador utiliza el árbol principal **`ST_NPC_Principal`** (ubicado en `Content/TFG_CastellanosSanchez/Blueprints/AI/StateTree`).

### 2.7.1 Estructura del `ST_NPC_Principal`
Para que el árbol de comportamientos funcione sin necesidad de escribir código visual (Blueprints), se apoya en tres pilares fundamentales que usted puede ver en el panel de Detalles del `ST_NPC_Principal`: **Contexto, Parámetros y Evaluadores**.

**1. El Contexto (Context)**
Define sobre "quién" se está ejecutando el árbol. Automáticamente, toma como referencia el **Actor** (el NPC) y su **AIController**. Estas referencias globales se inyectan hacia abajo, permitiendo que cualquier Tarea o Evaluador sepa exactamente a qué NPC está controlando.

**2. Parámetros del Árbol (Parameters)**
Son variables internas que actúan como la memoria a corto plazo de la IA. Por ejemplo:
* `RangeToEscapePistol` *(Float)*: La distancia (ej. 200.0) a la que el NPC considera que la pistola está lo suficientemente lejos como para sentirse a salvo, o huir o reaccionar de cerca.
* `Out_ReactionSequence` *(Booleano)*: Guarda si la secuencia de animaciones del data asset se quiere ejecutar en secuencia (true) o si solo se quiere ejecutar una animación random de la secuencia (false)
* `HasPlayedIntroReaction` *(Booleano)*: Una memoria para evitar que el NPC repita la animación inicial de, por ejemplo "susto", si el jugador no deja de apuntarle.

**3. Los Evaluadores (Sensores de la IA)**
Los evaluadores son el "sistema nervioso" del NPC. Se ejecutan en cada fotograma (*On Tick*) en el estado Raíz (*Root*), procesando el entorno y devolviendo variables de salida (`Salida` u `Output`) que el árbol utiliza para tomar decisiones instantáneas. Nuestra demo incluye:

* **`STE_CombatMonitor` (Prioridad 1 - Impactos):**
    * *Qué hace:* Se comunica con el componente de psicología.
    * *Variables de Salida:* `Out_GetHit` (¿Me han pegado?), `Out_SomeoneWasHit` (¿Han pegado a alguien cerca?), `Out_FrontHit` (¿El golpe viene de frente?). 
    * *Uso en la Jerarquía:* El primer estado del árbol lee `Si STE_CombatMonitor.Out_GetHit es True`. Si ocurre, bloquea el resto del árbol y fuerza la animación de impacto.
* **`STE_PlayerThreatMonitor` (Prioridad 2 - Amenazas):**
    * *Qué hace:* Vigila si el jugador está apuntando con un arma. Recibe como *Entrada* el parámetro `RangeToEscapePistol`.
    * *Variables de Salida:* `Out_IsReaction` (El jugador apunta), `Out_ShouldRun` (Está demasiado cerca, toca correr).
    * *Uso en la Jerarquía:* Si no hay combates, el árbol lee este evaluador. Si `Out_IsReaction` es *True*, transiciona al estado de huida si la pistola esta lejos o al estado de reacción si está muy cerca.
* **`STE_WeatherMonitor` (Prioridad 3 - Clima):**
    * *Qué hace:* Verifica el `BP_WeatherManager` y lanza un rayo virtual hacia arriba para saber si el NPC está a cubierto.
    * *Variables de Salida:* `Out_IsRaining` (¿Llueve?), `Out_IsOutside` (¿Estoy en la calle?).
    * *Uso en la Jerarquía:* Permite derivar al NPC hacia la casa o hacia una chimenea.
* **`STE_GetPatrolDetails` (Prioridad 4 - Rutina):**
    * * *Qué hace:* Lee el sistema de patrullas del nivel.
    * *Variables de Salida:* `Out_CurrentPatrolPoint` (Punto al que debo ir ahora).

### 2.7.2 Sistema de Patrullas Dinámicas (`BP_PatrolPoint`)

Para dotar al nivel de vida, el NPC necesita moverse de forma autónoma cuando no está reaccionando a un estímulo emocional. En lugar de programar coordenadas fijas en el código, hemos implementado un sistema utilizando el actor **`BP_PatrolPoint`**.

Este sistema permite al diseñador de niveles crear rutas complejas de forma visual directamente en el editor.

**1. ¿Qué es el `BP_PatrolPoint`?**
Es un Blueprint muy ligero que actúa como una baliza o destino. Contiene lógica interna para decirle al NPC hacia dónde debe ir después y cuánto tiempo debe descansar al llegar.

**2. Cómo crear un circuito de patrulla en su nivel:**
* Vaya a la carpeta `Content/TFG-Castellanos-Moreno-Sanchez\Editor`y abra el archivo `EUW_PatrolPoints` y corra el widget del editor, esto abrirá una ventana para ir creando PatrolPoints a partir del seleccionado.
* Vaya a la carpeta `Content/TFG_CastellanosSanchez/Blueprints/AI` y arrastre un **`BP_PatrolPoint`** a su escena.
* Seleccione el **PatrolPoint**. En su pantalla abierta del `EUW_PatrolPoints`, dale a **`Next Patrol Point`** y verá que se crea otro punto.
* Existe la opción de darle al boton de  **`Between Patrol Point`**, para ello deberá seleccionar un punto A y un punto C, creandose así un punto B. Por lo tanto el recorrido seria A -> B -> C y C -> B -> A
* Para cerrar el circuito y crear un bucle infinito, en el Punto C seleccione de nuevo el Punto A.

* En el punto 2.4.1 Variables Expuestas (Configuración en Editor) en las variables relacionadas con Patrol Points deciamos que más tarde se explicaría que instanciar. Pues ahora que sabemos que es un patrol point y como se crean en la escena, se recomienda poner varios puntos para la lista de Escape Patrol Points donde se crea que son buenos puntos de huida, como puede ser fuera de la casa. Una vez puestos se deberán instanciar en el editor en las variables de dicho apartado. Lo mismo haremos con el Fire Patrol Point, que sera el punto de la chimenea. En el caso de Actor to Follow se asignara el punto inicial de cada ruta creada, tiene que ser el primer puntos si o si. 

**3. Personalización del comportamiento por punto:**
En el panel de detalles de cada `BP_PatrolPoint` encontrará variables adicionales (como `WaitTime` o *Tiempo de espera*). Esto le permite crear un comportamiento orgánico: puede hacer que el NPC llegue a un punto y espere 5 segundos, pero que al llegar a otro punto continúe caminando inmediatamente (espera = 0). También hay una varibale de Gameplay Tag, para asignar un las animaciones que realizarán al llegar a dicho punto.

### 2.7.3 Modularidad: Linked Assets (Sub-Árboles)
Nuestra arquitectura es altamente modular. La lógica de combate y clima está encapsulada en **Linked Assets**. 
* **Aplicación Práctica:** Si usted crea su propio *State Tree* desde cero para un NPC diferente, no necesita reprogramar cómo huir de las armas. Simplemente arrastre nuestro estado "Linked Asset" a su árbol, y su nuevo NPC heredará automáticamente todas nuestras reacciones de supervivencia y análisis del GRU.

**El Flujo de Variables Hacia el Linked Asset:**
Un Linked Asset funciona como una "Caja Negra" a la que hay que inyectarle datos desde el árbol padre. Tomando como ejemplo nuestro Sub-árbol de Reacciones (`ST_NPC_Reactions`), este requiere recibir por parámetro las siguientes variables:

* **`bIsReaction` (Booleano):** Determina si existe una amenaza visual que requiera una reacción estática.
* **`bShouldRun` (Booleano):** Determina si la amenaza es tan crítica que el NPC debe huir.
* **`ReactionSequence` (Booleano):** Le dice al sub-árbol si quiere realizar el diccionario de animaciones en secuencia o coger una animación al azar.
* **`LoopStartIndexInSequence` (Entero) y `HasPlayedIntro` (Booleano):** Si se ha elegido que se va a realizar el diccionario de animaciones en secuencia, es posible que en dicha secuencia no se quiera repetir la animación inicial, ya sea porque es un susto y solo quieres que se haga la primera vez. Para ello es necesario pasar un entero para ver a partir de que animación realizas el bucle de la secuencia, y poner el booleano a true para saber que la animación incial ya se ha ejecutado una vez y quieres partir del indice establecido en `LoopStartIndexInSequence`.

**Jerarquía Interna del Linked Asset:**
Una vez inyectados estos parámetros, el Sub-árbol elige internamente qué hacer evaluando dichas condiciones:
1.  **`Run State`:** Se ejecuta inmediatamente `Si Parameters.bShouldRun es True`.
2.  **`Reaction State`:** Se ejecuta `Si Parameters.bIsReaction es True` (y la anterior fue falsa). Llama a la tarea interna de reproducir las animaciones alimentándola con las tags recibidas.
3.  **`Walk State` / `Wait`:** Si ambas condiciones booleanas son falsas, el NPC asume que el peligro ha pasado, procediendo a calmarse o caminar según corresponda, devolviendo finalmente el "Éxito en el árbol" para retornar al árbol principal.ia.

### 2.7.4 Modularidad Animada: Gameplay Tags y Data Assets

Uno de los mayores errores en el desarrollo de IA es "hardcodear" (fijar directamente en el código) las animaciones. Si le decimos al State Tree *"Reproduce la animación de huir de Pedro"*, ese State Tree ya no servirá para "María", porque intentará usar el esqueleto de Pedro.

Para resolver esto y hacer que nuestra IA sea escalable, la demo utiliza una arquitectura basada en **Gameplay Tags** y **Data Assets**. Esto permite que un único State Tree gobierne a infinitos NPCs, y que cada uno se anime con su propio estilo.

**1. Las Etiquetas (Gameplay Tags)**
Una *Gameplay Tag* es simplemente una etiqueta jerárquica (texto) que el motor reconoce globalmente. En lugar de decir "Reproduce Animación X", el State Tree ordena: *"Ejecuta la acción asociada a la etiqueta `Anim.Reaction.Scared`"*.

* *¿Cómo usarlo?* Si abre el Sub-árbol `ST_NPC_Reactions` y vas al estado de `Reaction State` veras que la tarea `STT_PlayMontage`, es capaz de acceder a un data asset si el Gameplay Tag actual del NPC coincide con algun data asset contenido en la lista del NPC. Para establecer el Gameplay Tag actual al NPC tiene dos formas: usando una tarea en un estado anterior llamada `STT_InstanceTagReaction`, como puedes ver en nuestro arbol  `ST_NPC_Principal` hay un estado como `Threat State` que instacia el Gameplay Tag actual a `NPC.Reactions.ReactFlinch` de esta forma el Play Montage reproducirá las animaciones del data assets vinculado con ese tag. Otra forma es que acceda al Gameplay Tag del Patrol Point en el que esta ubicado y haga alguna animación en ese momento.

**2. El Diccionario de Animaciones (Data Assets)**

Para que el NPC sepa qué animación física corresponde a esa etiqueta, utilizamos un **Data Asset**. Funciona como un diccionario de traducción personal de cada personaje.
* En el directorio del proyecto, encontrará Data Assets creados en `TFG-Castellanos-Sanchez\Blueprints\NPCs\DataAssets` a partir de una clase personalizada que vemos en `TFG-Castellanos-Sanchez\Blueprints\PrimaryDataAssets`.
* Si abre uno de estos Data Assets, verá:
  * **Clave (Key):** El Gameplay Tag (ej. `Anim.Reactions.Random`) con el se comparará en el `STT_PlayMontage` si tiene dicho data asset el NPC .
  * **Lista de Montage:** *Animations Montages* físicos que se reproducirán en el juego.

**3. Implementación para el usuario:**
Si usted quiere añadir nuevas animaciones o crear un NPC completamente nuevo con nuestro sistema, siga estos pasos:

1. **Crear su Diccionario:** Haga clic derecho en el Content Browser > *Miscellaneous* > *Data Asset*. Seleccione la clase de mapeo de animaciones que proporcionamos.
2. **Llenar el Diccionario:** Abra su nuevo Data Asset y añada tantas filas como necesite. Asigne una etiqueta (ej. `Anim.Reactions.Idle`) y añada en la lista *Animations Montages* de su propio personaje.
3. **Equipar al Cerebro:** Vaya al Blueprint de su nuevo NPC. Seleccione su componente principal de comportamiento o variables y busque la ranura para el Data Asset de animación. Arrastre ahí el archivo que acaba de crear.

**El resultado del flujo es instantáneo:** El State Tree dicta la lógica universal (Ej. "Has recibido un golpe, ejecuta la etiqueta `Anim.Hit`"). El NPC recibe la orden, consulta **su propio Data Asset**, encuentra la animación de dolor específica para su cuerpo, y la reproduce. No tendrá que reprogramar ni un solo nodo para añadir decenas de personajes distintos al juego.
---

# 3. Ampliación de Información y Referencia Técnica <a name="3-ampliación-de-información-y-referencia-técnica"></a>

A continuación se detalla la documentación técnica avanzada sobre los parámetros de configuración y los scripts ejecutables.

## 3.1 Configuración de parámetros (`config.ini`) <a name="31-configuración-de-parámetros-configini"></a>

### Bloque `[Dataset]` (Obligatorio)
| Parámetro | Descripción |
| :--- | :--- |
| **`CSV_NAME`** | Nombre del archivo CSV que contiene el dataset de entrenamiento. |
| **`TESTER_CSV_NAME`** | Nombre del archivo CSV para validación (se recomiendan datos independientes). |
| **`OUTPUT_NAMES`** | Nombre de las columnas objetivo (emociones que el modelo debe predecir). |
| **`SEQUENCE_LENGTH`** | Longitud de la secuencia de entradas para el entrenamiento del GRU. |
| **`BLOCK_SIZE`** | Tamaño de las entradas contiguas dentro del dataset. |

![Ref](Imagenes/Guia_1.png)

### Bloque `[Autoencoder]`
| Parámetro | Descripción |
| :--- | :--- |
| **`N_SYNTHETIC`** | Número de secuencias sintéticas generadas por el autoencoder. |
| **`EPOCHS`** | Iteraciones totales para el entrenamiento del autoencoder. |
| **`LATENT_SIZE`** | Dimensión del espacio latente. |
| **`HIDDEN_SIZE`** | Tamaño de las capas ocultas. |
| **`HIDDEN_NUM`** | Cantidad de capas ocultas en la arquitectura. |
| **`LEARNING_RATE`** | Tasa de aprendizaje (Learning rate). |
| **`BETA_VAE`** | Valor del parámetro beta utilizado en la función de pérdida. |
| **`BATCH_SIZE`** | Tamaño del lote (Batch) de procesamiento. |
| **`USE_CUDA`** | *True* para cálculo en GPU (Recomendado) o *False* para CPU. |

### Bloque `[GRU]`
| Parámetro | Descripción |
| :--- | :--- |
| **`EPOCHS`** | Iteraciones totales para el entrenamiento del modelo GRU. |
| **`HIDDEN_SIZE`** | Tamaño de las capas ocultas del modelo. |
| **`NUM_LAYERS`** | Número total de capas ocultas. |
| **`BATCH_SIZE`** | Tamaño del lote (Batch) de procesamiento. |
| **`LEARNING_RATE`** | Tasa de aprendizaje (Learning rate). |
| **`ACCURACY_THRESHOLD`**| Rango de tolerancia para considerar válida una salida. |
| **`USE_CUDA`** | *True* para cálculo en GPU o *False* para CPU. |

<br>

## 3.2 Referencia de Scripts de Ejecución <a name="32-referencia-de-scripts-de-ejecución"></a>

### `training.bat`
Script principal de pipeline para generación de datos y entrenamiento:
* Genera casos de prueba sintéticos a partir del dataset original.
* Aplica codificación *One-Hot* automáticamente a las columnas categóricas.
* Almacena los datos sintéticos como `generated_{nombre_dataset}`.
* Muestra un gráfico de dispersión en consola con la distribución de los nuevos datos.
* Entrena el modelo GRU y exporta los archivos necesarios para Unreal Engine (`gru_model.onnx` y `gru_model.onnx.data`) y un archivo `gru_model.pth` para testeos locales.

### `gru_only.bat`
Script para entrenamiento directo:
* Entrena el modelo utilizando exclusivamente los datos del dataset configurado, aplicando codificación *One-Hot*.
* Muestra por consola las matrices de confusión resultantes y el porcentaje de precisión (*Accuracy*) final del modelo.

### `testeo.bat`
Script de validación y auditoría:
* Carga el modelo `gru_model.pth` de la carpeta `models` y realiza predicciones usando el dataset de prueba indicado.
* Imprime por pantalla un análisis de correlación matemática entre las salidas reales del dataset de prueba y las inferidas por el modelo.
