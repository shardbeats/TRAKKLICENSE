# Informe — Alcance legal global de licencias TRAKKLICENSE

> Fecha: 2026-10-18. Solo informativo, NO es asesoría legal. Consulta abogado musical.
> Contexto: productor en México vendiendo beats mundialmente, con templates base BeatStars + template propio exclusive 10Y.

## 0. Respuesta corta

Sí puedes vender mundialmente desde México con contratos privados en inglés y cobro+entrega digital, como ya haces con BeatStars. El Convenio de Berna (180+ países) protege tu obra automáticamente sin registro, y el contrato rige la relación privada.

Pero "legal mundialmente" NO significa ejecución automática en todos lados: cada país aplica su ley de protección + sus formalidades, y un juicio mexicano es caro de ejecutar fuera. En la práctica el 95% de disputas beatmaker se resuelve en plataformas (takedowns, Content ID, distribuidoras), no en tribunales.

Tu riesgo no es el formato BeatStars, es la **evidencia**: BeatStars aporta logs de clickwrap + recibo + versión exacta del contrato. Fuera de BeatStars (DM/email con TRAKKLICENSE) debes replicar esa evidencia tú.

## 1. Base BeatStars (lo que ya usas)

- Templates default redactados por firma grande de music law (BeatStars dixit). Protegen a ambas partes.
- Cada productor opera como negocio independiente: BeatStars NO es parte ni responde por tu licencia.
- Non-exclusive = lease con caps; Exclusive típicamente **transfiere ownership del master** (buyer = nuevo dueño del master). Tus non-exclusive previas siguen válidas tras vender exclusive.
- Ojo discrepancia: tu template propio exclusive 10Y dice correctamente "license, NOT sale/buyout/transfer of ownership" (10 años, revierte). Eso es más restrictivo que el exclusive default BeatStars (transfer). No mezcles textos: decide por tier si exclusive = licencia temporal o transferencia, y mantenlo consistente en UI.

## 2. México (tu base)

- **Derechos morales inalienables** (LFDA art. 18-21): unidos al autor, inalienables, imprescriptibles, irrenunciables. NO puedes ceder tu paternidad ni integridad. Tu template lo respeta (ownership retained + credit "Prod. by"). Nunca prometas "full ownership transfer incl. moral rights" — nulo en México.
- Solo cedes **patrimoniales** (reproducción, distribución, comunicación pública, sincronización). Crédito siempre obligatorio (art. 57).
- Obra musical con letra/música 50/50 salvo pacto (art. 81-83). Tu 50/50 writer/publisher split es estándar y compatible.
- **Firma electrónica válida** (Código de Comercio art. 89-114, reforma 2003): equivalencia funcional + neutralidad tecnológica. Mensaje de datos = escrito si íntegro + accesible + atribuible. Firma electrónica = mismos efectos que autógrafa si: vinculada solo al firmante, bajo su control al firmar, alteración detectable (art. 97). Firma simple (click + email) SÍ vale pero es la más débil ante juez; avanzada/FIEL es fuerte.
- Contrato en inglés entre mexicano y extranjero: válido si hubo consentimiento, pero en juicio mexicano se interpreta en español y la parte débil puede alegar incomprensión. Recomendación: bilingüe o cláusula "English prevails, Spanish translation attached".
- Conservación: NOM-151 para mensajes de datos (integridad + accesibilidad 10 años en comercial).

## 3. Validez fuera (EEUU / UE / resto)

- **EEUU (ESIGN + UETA)**: clickwrap generalmente enforceable. Doctrina 2024-2025 (Domer 7th Cir; Experian 4th/11th Cir): vale si (a) aviso razonablemente conspicuo + (b) asentimiento inequívoco ligado al pago (checkbox "I agree" ideal, híbrido "By purchasing you accept + link" también vale pero más débil). Debes guardar la copia autoritativa exacta versionada (UETA §16): muchos pierden por presentar versión equivocada.
- **UE (eIDAS)**: firma simple válida, pero valor probatorio bajo; cualificada/avanzada + timestamp = fuerte. GDPR si guardas datos de buyer UE (minimiza, borra a pedido).
- **Berna**: trato nacional — tu obra mexicana protegida en cada país miembro como si fuera nacional, pero infracción se juzga con ley del país de protección. Cláusula "worldwide license" es estándar y válida; "governing law = United Mexican States" también válida entre privados, pero ejecutar sentencia MX en EEUU/UE requiere exequátur (caro/lento). Por eso añade mediación/arbitraje opcional + jurisdicción alternativa (ej. Texas/California si tu comprador es US).
- Impuestos: retenciones US (W-8BEN), IVA digital UE, ISR/IVA MX. El app no retiene, pero avisa "buyer responsible for taxes".

## 4. Tu cláusula "pago = aceptación, sin firma" (Sec. 25)

Común en leases y aceptada como clickwrap/hybrid-wrap si: (1) texto conspicuo antes del pago "By completing purchase you accept [link] terms", (2) checkbox separado ideal, (3) guardas PDF exacto + hash SHA256 + fecha/hora + IP + email + recibo + entrega. Sin eso es la forma más débil y un chargeback te deja sin prueba. Mejora mínima ya prevista en TRAKKLICENSE: `rendered_text` guardado + export con nombre único; falta añadir hash + log de aceptación en v0.5.

## 5. Riesgos del software (top 10) + mitigación en app

1. **Parecer asesoría legal** → disclaimer fijo en UI + PDF ("informational, consult attorney"), sin promesas de validez.
2. **Evidencia débil** → WORM history (no editar tras vender), hash SHA256 del PDF, log (fecha, IP, email, versión template), copia autoritativa versionada.
3. **Samples sin clearance (Sec. 18)** → campo `{SAMPLES}` obligatorio ("None declared" explícito), warranty + buyer-clearance clause ya la tienes; no generes si vacío sin confirmar.
4. **Conflicto exclusive vs leases previos / Content ID** → tu Sec. 5 (previas siguen válidas) es correcta; añade aviso en UI al vender exclusive si hay sales previas del mismo beat + bloqueo Content ID para non-exclusive.
5. **Menores/incapacidad** → checkbox 18+ o tutor, campo país.
6. **PROs (SACM/BMI/ASCAP)** → splits del contrato deben igualar registros; 50/50 no se auto-registra, el artista debe registrar. Añade recordatorio.
7. **Idioma/jurisdicción** → selector `{STATE_PROVINCE_COUNTRY}` + `{COUNTRY}` ya existe; añade plantilla ES + opción arbitraje.
8. **Expiración 10Y** → tu Sec. 11 revierte derechos; app debe alertar renovación (calendario + email manual v2).
9. **Privacidad** → LFPDPPP/GDPR: solo local, borrado a pedido, sin telemetría (ya es offline-first, mantener).
10. **Consumidor/chargebacks** → "no refunds digital goods" vale salvo ley aplicable; guarda prueba de entrega (link/descarga) + recibo.

## 6. Recomendaciones concretas v0.5 (sin romper ligero)

- Checkbox "I have read and agree" + link al PDF exacto antes de Export/Save; guarda `accepted_at + hash + template_version`.
- SHA256 en `sales` + nombre `TRAKKLICENSE_{beat}_{cust}_{date}_{hash8}.pdf`.
- Plantilla ES espejo + cláusula idioma prevalente.
- Selector governing law (MX por defecto, US-TX/US-CA, ES) + arbitraje opcional.
- Bloqueo edición de sale guardada (solo re-generar como nueva versión).
- Recordatorios: 10Y expiry, PRO registration, taxes.

## 7. Fuentes consultadas

- help.beatstars.com: Content Licenses FAQs; Can non-exclusive survive exclusive; Reset license to default template (law firm drafted).
- tools4music.com 2026-05-22 (13 cláusulas WAV lease), hireggie.com (contract codes + ejemplo).
- LFDA art. 11-13, 18-21, 42-59, 81 (moral inalienable, edición musical); Código de Comercio art. 89-114 (firma/mensaje datos); CMS/Holland&Knight e-sign MX; Lexology commercial contracts MX.
- US: ESIGN/UETA, Domer v. Menard 7th Cir 2024 (5-factor notice), Experian 4th/11th Cir 2025, NCLC challenge keys (authoritative copy §16).
- WIPO Berna + PIL (ley país protección, trato nacional).

---
*Guardar evidencia > ganar juicio. El alcance es global para licenciar, territorial para litigar.*
