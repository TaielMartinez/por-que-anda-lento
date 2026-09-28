# Admin obligatorio con auto-elevación

El Colector exige privilegios de administrador en lugar de funcionar degradado sin ellos, porque los datos que más importan para la lentitud (procesos del sistema, pool por tag, trazas ETW, varios logs de eventos) salen incompletos o no salen sin admin. Como el agente que lo lanza normalmente corre sin elevación, el Colector se auto-eleva con UAC: el proceso original espera al elevado y devuelve la ruta de la Captura, así el flujo del agente no se corta y al usuario le cuesta un clic.

## Considered Options

- Funcionar sin admin y marcar en el manifest qué faltó: descartado; las Capturas parciales serían la norma.
- Fallar sin admin y pedir al usuario una terminal elevada: descartado; corta el flujo del agente.
