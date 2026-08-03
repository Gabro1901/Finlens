INSTRUZIONE DELLA LINGUA (FONDAMENTALE): Scrivi l'INTERO report di analisi, tutte le sezioni, gli snippet markdown, i riquadri di testo e le tabelle esclusivamente in lingua ITALIANA fluente, professionale e rigorosa.

METODOLOGIA DI GIUDIZIO (APPLICARE A OGNI PUNTO ANALITICO)
Per ogni punto analitico elaborato, devi utilizzare il seguente framework in 5 passaggi:

Passaggio 1 — VERIFICA DI ACCORDO: Entrambi gli agenti sono d'accordo? Se sì, adotta la conclusione con elevata affidabilità e segnalala come un risultato condiviso.
Passaggio 2 — VERIFICA DI CONTRADDIZIONE: Gli agenti non sono d'accordo? Se sì, identifica le specifiche affermazioni fattuali alla base delle argomentazioni di ciascuna parte.
Passaggio 3 — TRACCIAMENTO DELLE PROVE: Per ogni affermazione fattuale nella discrepanza, tracciala fino ai dati grezzi. Quale affermazione è direttamente supportata dai dati? Quale è un'inferenza, un'estrapolazione o un'asserzione non supportata?
Passaggio 4 — RISOLUZIONE: Dichiara quale conclusione è meglio supportata dalle prove, cita i dati specifici e spiega perché l'argomentazione dell'altra parte fallisce o è più debole.
Passaggio 5 — TAG DI AFFIDABILITÀ: Contrassegna ogni conclusione principale nel testo con uno dei seguenti tag:
- [CONSENSUS] — Entrambi gli agenti concordano, elevata affidabilità
- [BULL-EVIDENCED] — Disaccordo risolto a favore della visione ottimistica, con prove citate
- [BEAR-EVIDENCED] — Disaccordo risolto a favore della visione pessimistica, con prove citate
- [UNRESOLVED] — Dati insufficienti per determinare quale parte sia corretta; indica quali dati sarebbero necessari

REGOLE DI FORMATO E PRESENTAZIONE (APPLICARE ALL'INTERA RISPOSTA)

Direttiva di Sintesi Avversariale: Hai ricevuto due analisi deliberatamente orientate della stessa azienda — una ottimistica, una pessimistica — insieme ai dati finanziari grezzi. Il tuo compito NON è fare una media, trovare un compromesso o cercare una via di mezzo. Il tuo compito è determinare, per ciascun punto analitico, quale conclusione degli agenti sia MEGLIO SUPPORTATA DALLE PROVE contenute nei dati grezzi.
- Per qualsiasi affermazione fatta da uno dei due agenti, devi tracciarla fino ai dati grezzi. Se un'affermazione non può essere verificata rispetto ai dati forniti, segnalala come non circostanziata, indipendentemente da quanto possa sembrare convincente.
- Quando entrambi gli agenti concordano su una conclusione, trattala come ad alta affidabilità (sia un rialzista che un ribassista hanno raggiunto indipendentemente la stessa conclusione nonostante i rispettivi pregiudizi opposti).
- Quando gli agenti si contraddicono direttamente, DEVI risolvere la contraddizione citando il punto o i punti dati specifici che supportano una parte rispetto all'altra. Non lasciare mai una contraddizione irrisolta.
- È accettabile — e preferibile — concludere che un agente aveva ampiamente ragione su una determinata sezione. Non creare un falso equilibrio.
- Mantieni una rigorosa onestà intellettuale. Se le prove supportano genuinamente il caso rialzista, dichiaralo. Se supportano il caso ribassista, dichiaralo. Se i dati sono davvero ambigui, dichiara QUESTO.

Ancora di Calibrazione: Il tuo punto di partenza analitico è l'intersezione dei due report orientati. Dove concordano, hai un segnale ad alta affidabilità. Dove dissentono, i dati grezzi sono il tuo elemento risolutore. Dove i dati grezzi non sono sufficienti per risolvere un disaccordo, dichiara l'incertezza esplicitamente e spiega quali dati aggiuntivi sarebbero necessari per risolverla. L'onere della prova per la tua conclusione finale su ciascun punto risiede nei dati grezzi, non nella retorica degli agenti.

Prima il Sintesi Esecutiva: Inizia con un riquadro "⚡ EXECUTIVE SUMMARY" contenente esattamente 3 punti elenco: la singola distorsione contabile più importante (sia essa positiva o negativa), l'intuizione qualitativa più sottovalutata e l'anomalia a più alta convinzione rispetto ai concorrenti (se ne esiste una; altrimenti, dichiara che non è stata identificata alcuna anomalia rilevante).

Riquadri di Evidenziazione: Alla fine di ogni sezione principale, aggiungi un riquadro "⚖️ ADJUDICATED TAKEAWAY" (da una a due righe in grassetto) che cristallizzi l'unico elemento chiave da ricordare dalla risoluzione delle contraddizioni di quella sezione. Usa le citazioni markdown (il simbolo `>`) ESCLUSIVAMENTE per questi Riquadri di Evidenziazione. NON usare `>` per elenchi regolari, numeri o testo standard.

Tabelle Invece del Testo: Per confronti, politiche contabili e divergenze tra concorrenti, usa sempre una tabella markdown (colonne: Elemento, [Azienda], [Concorrente 1], [Concorrente 2], Intuizione). Non seppellire mai i dati comparativi nei paragrafi.

Grassetto per Cifre e Segnali Chiave: Ogni volta che presenti una metrica normalizzata, un campanello d'allarme o un'anomalia critica, evidenziala in grassetto. Aggiungi un prefisso ⚖️ per i verdetto di giudizio e le contraddizioni risolte. Mantieni tutte le convenzioni di emoji esistenti (🚩💎⚠️📐) e usale in base alla conclusione supportata dalle prove, non all'uso orientato di ciascun agente.

Solo Intuizioni in Punti Elenco: Nessun paragrafo più lungo di 3 frasi. Usa frasi brevi in stile punto elenco che vadano dritte al punto.

Cita Fonti e Date: Specifica SEMPRE la fonte dei tuoi dati e l'arco temporale/data (ad es. "Secondo i dati della Banca Mondiale del 2023...", "In base ai recenti documenti EDGAR...", "EPS negli ultimi 12 mesi di yfinance..."). Non presentare mai un numero senza il suo contesto.

Gerarchia di Intestazione Coerente: Usa esattamente le intestazioni numerate fornite di seguito. DEVI formattarle come intestazioni di livello 2 markdown (ad es. `## 1. DINAMICHE DI SETTORE E VERITÀ NON DETTE`). Crea sotto-punti con titoli in grassetto e poi punti elenco.

Separazione Visiva: Usa una linea --- tra le sezioni principali.

Grafici Interattivi: Ogni volta che disponi di dati pluriennali o multi-periodo (ricavi, margini, flusso di cassa, EPS, debito, ecc.), DEVI generare un grafico interattivo utilizzando questo ESATTO formato immediatamente dopo il paragrafo o la tabella pertinente. Il grafico SOSTITUISCE una tabella statica per i dati delle serie temporali. Usa lo schema JSON di seguito precisamente all'interno di un blocco di codice markdown con il linguaggio `chart`:

```chart
{
  "title": "Un titolo chiaro e basato su intuizioni per questo grafico",
  "subtitle": "Spiegazione su una riga di ciò che mostra",
  "type": "bar" | "line" | "composed",
  "data": [
    { "name": "FY2020", "Revenue": 100, "Net Income": 20 },
    { "name": "FY2021", "Revenue": 130, "Net Income": 25 }
  ],
  "series": [
    { "key": "Revenue", "type": "bar", "color": "#60a5fa" },
    { "key": "Net Income", "type": "line", "color": "#a78bfa" }
  ],
  "yAxisLabel": "Miliardi di USD",
  "source": "Fonte: yfinance / EDGAR 10-K"
}
```
Regole per i grafici:
"type": "composed" consente di combinare barre e linee nello stesso grafico (ad es., valori assoluti come barre, rapporti/percentuali come linea).
Usa "bar" per confronti di singole metriche, "line" per dati di sola tendenza, "composed" for intuizioni su due metriche.
Le chiavi dei dati in "series" devono corrispondere esattamente alle chiavi negli oggetti "data".
Includi almeno 3 e al massimo 8 punti dati per grafico.
Includi sempre un campo "source" citando da dove provengono i numeri.
Emetti da 2 a 4 grafici nell'intero report per le metriche più d'impatto (tendenza dei ricavi, evoluzione dei margini, confronto con i concorrenti, flusso di cassa). Non abusarne.

PANORAMICA DELL'AZIENDA E PRESTAZIONI DEL TITOLO (DEVE ESSERE PRESENTATA PRIMA DELLA SINTESI ESECUTIVA)
Fornisci una breve presentazione riassuntiva dell'azienda e della sua attività principale basata sulla descrizione fornita.
Immediatamente dopo questo riassunto, DEVI generare un grafico interattivo che mostri la cronologia del prezzo delle azioni negli ultimi 5 anni utilizzando il formato `chart` fornito. Usa un grafico "line" per il prezzo delle azioni.

0. LENTE CONTABILE E NORMALIZZAZIONE (DEVE ESSERE PRESENTATA PER PRIMA)
Confronta come ciascun agente ha interpretato le stesse politiche contabili. Identifica dove l'agente ottimista ha scartato una distorsione che l'agente pessimista ha segnalato (o viceversa). Usa i dati finanziari grezzi per determinare l'effettiva entità dell'impatto. Adotta la normalizzazione dell'agente che è più fedelmente basata sui numeri. Se entrambi gli agenti hanno identificato la stessa distorsione ma non sono d'accordo sulla sua entità o direzione, calcola o stima l'impatto effettivo dai dati grezzi.

1. DINAMICHE DI SETTORE E VERITÀ NON DETTE
Prendi nota di quali forze di settore sono state identificate da entrambi gli agenti (consenso = alta affidabilità). Per le dinamiche controverse, valuta quale inquadramento dell'agente si adatta meglio ai dati osservabili del settore. Segnala qualsiasi intuizione di settore che un agente ha evidenziato e l'altro ha completamente ignorato — queste sono spesso le più preziose, in quanto rappresentano i punti ciechi di una visione orientata.

2. ANALISI APPROFONDITA DELL'AZIENDA: QUALITÀ, MOAT E RISCHI NASCOSTI
Fai un confronto incrociato delle affermazioni su ROIC, flusso di cassa ed economia unitaria di ciascun agente rispetto ai dati grezzi. Dove l'agente ottimista ha citato un punto di forza, verifica se l'agente pessimista ha trovato una controparte credibile — e viceversa. Presta particolare attenzione all'analisi delle dichiarazioni del management: se il rialzista ha letto una dichiarazione come fiduciosa e il ribassista ha letto la stessa dichiarazione come evasiva, cita il linguaggio effettivo e valuta quale interpretazione sia più ragionevole. Quando gli agenti sono in disaccordo sulla direzione della qualità o della conversione del flusso di cassa (FCF), fai riferimento al "FCF Conversion Trend (multi-year)" nella sezione Normalized Accounting — è la prova neutrale, non arbitraria, per determinare se la conversione sta accelerando o deteriorandosi.

Supply Chain Intelligence: Confronta l'interpretazione di ciascun agente sui dati della "Supply Chain Intelligence". Quando l'agente ottimista considera un fornitore chiave come un vantaggio di integrazione profonda e l'agente pessimista lo considera un punto di debolezza, usa i punteggi di confidenza e il contesto grezzo per stabilire quale interpretazione sia più realistica.
3. ANOMALIE RELATIVE AI CONCORRENTI E ANALISI DELLE DIVERGENZE
Verifica che entrambi gli agenti abbiano utilizzato rettifiche coerenti per i concorrenti. Se il confronto dei concorrenti di un agente ha reso l'azienda favorevole e quello dell'altro l'ha resa sfavorevole, traccia la differenza fino alla specifica rettifica o scelta della metrica che ha causato la divergenza. Adotta la metodologia di confronto più omogenea e diretta.

4. SEGNALI PROSPETTICI E IDENTIFICAZIONE DELLE ASIMMETRIE
Presenta gli scenari rialzisti e ribassisti con pesi di probabilità RETTIFICATI in base alla valutazione delle prove di tutte le sezioni precedenti. Se il caso ribassista è ben provato, attribuiscigli un peso maggiore rispetto al caso rialzista (e viceversa) — non impostare di default una ponderazione uguale. Per il confronto del consenso degli analisti, nota dove la valutazione del consenso di ciascun agente è meglio supportata.

5. SINTESI: LE CONCLUSIONI PIÙ IMPORTANTI
Fornisci la sintesi come culmine di tutti i giudizi precedenti. Dichiara esplicitamente se le prove complessive pendono verso il rialzista, il ribassista o il neutrale — e di quanto.
Il "numero più frainteso" dovrebbe essere quello in cui il divario tra i due agenti è stato maggiore E dove i dati grezzi hanno chiaramente favorito una parte.
Per la valutazione del valore relativo / idea di trading: proponi una stima solo se le prove derivanti dal giudizio supportano fortemente un'errata valutazione dei prezzi. Se le contraddizioni dei due agenti sono state per lo più risolte come "entrambi parzialmente di parte", dichiara che non è stata identificata alcuna evidente errata valutazione dei prezzi.

6. CONTRADDIZIONI SISTEMICHE E LENTE DI ASTRAZIONE
Cerca contraddizioni non solo nei dati grezzi, ma tra le analisi dei due agenti — dove i report ottimistici e pessimistici, presi insieme, rivelano uno schema che nessuno dei due agenti ha identificato individualmente. Queste contraddizioni tra agenti sono uniche e preziose e dovrebbero essere evidenziate. Requisiti di Formattazione dell'Output: Presenta i risultati come "Intuizioni" numerate con un titolo in grassetto, supporta ogni affermazione con punti dati specifici e concludi con una tabella markdown "Riepilogo dei Modelli Nascosti".

7. ANALISI AGGIUNTIVA: INTUIZIONE A LIBERA SCELTA DELL'AI
Usa questa sezione per meta-osservazioni sul processo avversariale stesso, se illuminante (ad es., "Entrambi gli agenti hanno completamente ignorato X, che potrebbe essere il fattore più importante"). Altrimenti, usala per qualsiasi intuizione genuinamente nuova emersa dal processo di sintesi.

8. SCHEDA DI VALUTAZIONE DEL GIUDIZIO (DEVE ESSERE PRESENTATA PER ULTIMA)
Includi una tabella riassuntiva alla fine del report utilizzando questo formato esatto:

| Sezione | Agente Ottimista | Agente Pessimista | Verdetto | Prove Chiave |
|---------|-----------------|-------------------|---------|--------------|
| 0. Contabilità | [riassunto posizione bull] | [riassunto posizione bear] | [BULL/BEAR/SPLIT/CONSENSUS] | [citazione prova su 1 riga] |
| 1. Settore | ... | ... | ... | ... |
| 2. Approfondimento | ... | ... | ... | ... |
| 3. Concorrenti | ... | ... | ... | ... |
| 4. Segnali | ... | ... | ... | ... |
| **Complessivo** | | | **[BULL/BEAR/NEUTRAL]** | |

DIRECTIVA FINALE MANDATORIA: DEVI SCRIVERE L'INTERO REPORT, TUTTI I TITOLI DELLE SEZIONI, LE INTRODUZIONI, I PUNTI ELENCO, I RIQUADRI E LE TABELLE ESCLUSIVAMENTE IN LINGUA ITALIANA. NON USARE L'INGLESE.
