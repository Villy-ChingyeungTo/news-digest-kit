"""Generate a fictional offline showcase; no configuration, network or mail."""
import datetime as dt
import json
from pathlib import Path
from ui import browser_preview

def main():
    clock=dt.datetime(2026,10,25,9,tzinfo=dt.timezone(dt.timedelta(hours=8)))
    examples=[
        ('AI infrastructure spending: a research watchlist','Bloomberg Technology',1),
        ('Global equities: earnings expectations in focus','Bloomberg Markets',2),
        ('Rates and inflation: signals for the morning briefing','Bloomberg Economics',3),
        ('Semiconductor supply chain: tracking capacity plans','Bloomberg Technology',14),
        ('Currency moves: a cross-asset research checklist','Bloomberg Markets',15),
        ('Energy transition: monitoring capital expenditure','Bloomberg Green',20),
    ]
    articles=[dict(url='https://www.bloomberg.com/',title='[FICTIONAL DEMO] '+title,
                   published=(clock-dt.timedelta(hours=hours)).isoformat(),
                   sections=json.dumps([section]),sent=None) for title,section,hours in examples]
    sources=[dict(name=s,status='ok',count=sum(a['sections']==json.dumps([s]) for a in articles)) for s in sorted({s for _,s,_ in examples})]
    output=Path(__file__).with_name('sample-preview.html')
    output.write_text(browser_preview(articles,sources,clock,sample=True),encoding='utf-8')
    print('Fictional offline demo:',output.name)

if __name__=='__main__':main()
