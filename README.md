# Silea Raccolta Rifiuti

Integrazione per Home Assistant che legge il calendario della raccolta porta a porta di
[Silea](https://www.sileaspa.it/calendario-raccolta-rifiuti/) (provincia di Lecco) per la tua via.

Non è un'integrazione ufficiale di Silea: usa gli stessi dati della pagina "Calendario raccolta rifiuti" del sito.

## Cosa crea

Per ogni via configurata:

| Entità | Cosa mostra |
|---|---|
| `calendar.…_calendario` | Un evento per ogni tipo di rifiuto ritirato, con orario e note di Silea |
| `sensor.…_prossimo_ritiro` | Data del prossimo ritiro; negli attributi i tipi, i giorni mancanti e le note |
| `sensor.…_da_esporre` | Cosa portare fuori: i ritiri di domani, o di oggi finché non sono conclusi. "Niente" se non c'è nulla |
| `sensor.…_prossimo_umido`, `_carta`, `_vetro`, `_plastica`, `_indifferenziato` | Data del prossimo passaggio di ogni tipo |

Un ritiro di oggi conta come passato dopo l'orario di fine indicato da Silea (di solito 13:30).
I dati si aggiornano ogni 12 ore. Di default vengono scaricati 4 mesi; si cambia dalle opzioni dell'integrazione.

## Installazione

Con HACS:

1. HACS → menu ⋮ → *Repository personalizzati* → aggiungi `https://github.com/MCoLoL/silea-rifiuti`, categoria *Integrazione*.
2. Installa **Silea Raccolta Rifiuti** e riavvia Home Assistant.
3. *Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Silea Raccolta Rifiuti*, poi scegli comune e via.

A mano: copia `custom_components/silea_rifiuti` nella cartella `custom_components` di Home Assistant e riavvia.

## Esempio: avviso la sera prima

```yaml
triggers:
  - trigger: time
    at: "20:00:00"
conditions:
  - condition: not
    conditions:
      - condition: state
        entity_id: sensor.raccolta_rifiuti_da_esporre
        state: "Niente"
  - condition: state
    entity_id: sensor.raccolta_rifiuti_da_esporre
    attribute: quando
    state: domani
actions:
  - action: notify.notify
    data:
      title: Stasera porta fuori
      message: "{{ states('sensor.raccolta_rifiuti_da_esporre') }}"
```

## Licenza

MIT. Vedi [LICENSE](LICENSE).
