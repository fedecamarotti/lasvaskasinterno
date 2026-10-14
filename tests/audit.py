import sys,os
from playwright.sync_api import sync_playwright
mock=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'mock-firebase.js')).read()
role=sys.argv[1] if len(sys.argv)>1 else 'admin'
res=[]
def ok(name,cond): res.append(('PASS' if cond else 'FAIL',name)); 
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1300,'height':900})
    errs=[]; pg.on('pageerror',lambda e:errs.append('JS:'+str(e))); pg.on('dialog',lambda d:(errs.append('DIALOG:'+d.message),d.accept()))
    pg.route('**/*',lambda r: r.fulfill(body='',content_type='application/javascript') if ('gstatic' in r.request.url or 'html2canvas' in r.request.url) else (r.continue_() if r.request.url.startswith('file') else r.abort()))
    pg.add_init_script(f"window.__ROLE='{role}';"); pg.add_init_script(mock)
    pg.goto('file://'+os.environ.get('INDEX',os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','index.html'))); pg.wait_for_timeout(500)
    ev=pg.evaluate
    txt=lambda sel: ev(f"document.querySelector('{sel}').innerText.replace(/\\s+/g,' ')")
    wait=lambda n=250: pg.wait_for_timeout(n)
    ok('lista inicial',  'Arana' in txt('#clientas-list') and 'Cosentino' in txt('#clientas-list'))
    # crear clienta
    ev("openClientaModal()"); wait(100)
    pg.fill('#clienta-nombre','Ana'); pg.fill('#clienta-apellido','Zeta'); pg.fill('#clienta-telefono','1155')
    ev("saveClienta()"); wait()
    ok('clienta creada visible', 'Zeta' in txt('#clientas-list'))
    ok('clienta en store', ev("Object.values(window.__store).some(x=>x.apellido==='Zeta')"))
    # sin telefono
    ev("openClientaModal()"); wait(100)
    pg.fill('#clienta-nombre','Bea'); pg.fill('#clienta-apellido','Yy'); ev("saveClienta()"); wait()
    ok('sin telefono: '+('permitido' if role=='admin' else 'bloqueado'), ('Yy' in txt('#clientas-list'))==(role=='admin'))
    # editar clienta
    ev("openClienteDetail('c1')"); wait()
    ev("openClientaModal(currentClienteData)"); wait(100)
    pg.fill('#clienta-telefono','9999'); ev("saveClienta()"); wait()
    ok('editar clienta', '9999' in txt('#client-header-box'))
    # presupuesto
    ev("openDocModal('presupuesto')"); wait(100)
    pg.fill('.pd-desc','copa'); pg.fill('.pd-efvo','10000'); ev("document.querySelector('.pd-efvo').dispatchEvent(new Event('input'))")
    ev("saveDoc()"); wait(400)
    ok('presupuesto en ficha', 'copa' in txt('#docs-list') or 'PRESUPUESTO' in txt('#docs-list').upper())
    ok('presupuesto global', ev("Object.keys(window.__store).some(k=>k.startsWith('presupuestos/'))"))
    ev("closeModal('modal-preview')")
    # venta con pago parcial
    ev("openDocModal('venta')"); wait(100)
    pg.fill('#doc-fecha','2026-09-02'); pg.fill('.pd-desc','vaso'); pg.fill('.pd-cant','2'); pg.fill('.pd-valorunit','50000')
    ev("document.querySelector('.pd-valorunit').dispatchEvent(new Event('input'))")
    ev("addPagoRow()"); ev("document.querySelector('#pagos-container select').value='EFVO_ARS'")
    ev("document.querySelector('#pagos-container input').value='40.000'; document.querySelector('#pagos-container input').dispatchEvent(new Event('input'))")
    ev("saveDoc()"); wait(400); ev("closeModal('modal-preview')")
    ok('venta deuda 60000', 'Debe' in txt('#docs-list') and '60.000' in txt('#docs-list'))
    cod=ev("docsCache.find(d=>d.tipo==='venta').codigo"); ok('codigo mes 09 (%s)'%cod, str(cod).startswith('09') or cod=='-')
    # deuda en lista de clientas
    ev("goBackToClientas()"); wait()
    ok('deuda en lista', '60.000' in txt('#clientas-list'))
    # editar venta
    ev("openClienteDetail('c1')"); wait()
    vid=ev("docsCache.find(d=>d.tipo==='venta').id")
    ev(f"openDocModal('venta', docsCache.find(d=>d.id==='{vid}'))"); wait(100)
    pg.fill('.pd-valorunit','60000'); ev("document.querySelector('.pd-valorunit').dispatchEvent(new Event('input'))")
    ev("saveDoc()"); wait(400); ev("closeModal('modal-preview')")
    ok('editar venta -> total 120000', '120.000' in txt('#docs-list'))
    # pago
    if role=='admin':
        ev("openPagoModal()"); pg.select_option('#pago-metodo-select','TRBF'); pg.fill('#pago-monto-input','80000'); ev("savePago()"); wait(300)
        ok('pago de 80.000 salda la venta de 120.000 (40.000 + 80.000)', ev("docsCache.find(d=>d.tipo==='venta').saldado===true"))
        pid=ev("docsCache.find(d=>d.tipo==='pago').id")
        ev(f"openPagoModal('{pid}')"); pg.fill('#pago-monto-input','100000'); ev("savePago()"); wait(300)
        ok('editar pago -> saldado', ev("docsCache.find(d=>d.tipo==='venta').saldado===true"))
        ev(f"openPagoModal('{pid}')"); ev("deletePago()"); wait(300)
        ok('borrar pago restaura deuda', ev("docsCache.find(d=>d.tipo==='venta').aPagarARS")==80000-0 or ev("docsCache.find(d=>d.tipo==='venta').aPagarARS")>0)
    # notas
    ev("openNotaModal()"); pg.fill('#nota-texto','hola nota'); ev("saveNota()"); wait(300)
    ok('nota creada', 'hola nota' in txt('#docs-list'))
    nid=ev("docsCache.find(d=>d.tipo==='nota').id"); ev(f"openNotaModal('{nid}')"); pg.fill('#nota-texto','nota editada'); ev("saveNota()"); wait(300)
    ok('nota editada', 'nota editada' in txt('#docs-list'))
    ev(f"openNotaModal('{nid}')"); ev("deleteNota()"); wait(300)
    ok('nota borrada', 'nota editada' not in txt('#docs-list'))
    # planillas
    ev("ventaMonth=new Date(2026,8,1); openVentasSheet()"); wait(400)
    ok('venta en planilla', 'vaso' in txt('#venta-sheet-body'))
    ev("presuMonth=new Date(); presuMonth.setDate(1); openPresupuestosSheet()"); wait(400)
    ok('presupuesto en planilla', 'copa' in txt('#presu-sheet-body'))
    # deudas
    ev("openDeudas()"); wait(300)
    ok('deudoras muestra', 'Arana' in txt('#deudas-list') or 'Amherdt' in txt('#deudas-list') or '$' in txt('#deudas-list'))
    # eliminar venta
    ev("openClienteDetail('c1')"); wait()
    ev(f"openDocModal('venta', docsCache.find(d=>d.id==='{vid}'))"); wait(100); ev("deleteDoc()"); wait(300)
    ok('venta eliminada', not ev("docsCache.some(d=>d.tipo==='venta')") and not ev("Object.keys(window.__store).some(k=>k==='ventas/%s')"%vid))
    # eliminar clienta
    ev("openClienteDetail('c2')"); wait()
    ev("openClientaModal(currentClienteData)"); wait(100); ev("deleteClienta()"); wait(400)
    ok('clienta eliminada', 'Cosentino' not in txt('#clientas-list'))
    # CC: remito normal con totales; en movimientos solo texto en Producto
    ev("openClienteDetail('c1')"); wait()
    ev("openDocModal('venta')"); wait(100)
    pg.fill('#doc-fecha','2026-09-06'); pg.select_option('#doc-puntoventa','CC')
    ok('CC: el formulario mantiene cant/precio/total', ev("getComputedStyle(document.querySelector('.prod-row .c-cant')).display")!='none')
    ok('no existe el boton + Punto de venta', ev("!document.getElementById('add-pv-btn') && ![...document.querySelectorAll('.add-pill')].some(b=>/Punto de venta/.test(b.innerText))"))
    pg.fill('.pd-desc','blusa 500 efectivo'); pg.fill('.pd-cant','1'); pg.fill('.pd-valorunit','500')
    ev("document.querySelector('.pd-valorunit').dispatchEvent(new Event('input'))")
    ev("addArregloRow()"); ev("document.querySelector('.ar-desc').value='arreglo cc'; document.querySelector('.ar-valor').value='300'; document.querySelector('.ar-valor').dispatchEvent(new Event('input'))")
    ok('total en vivo suma producto + arreglo (800)', '800' in ev("document.getElementById('doc-live-total').innerText"))
    ev("saveDoc()"); wait(500)
    v=ev("docsCache.filter(d=>d.tipo==='venta').find(d=>(d.productos||[]).some(p=>p.desc==='blusa 500 efectivo'))")
    ok('CC guarda cantidad/valor/total normales', v and v['productos'][0]['total']==500 and v['totalARS']==800 and v['productos'][0]['puntoVenta']=='CC')
    ok('remito CC con columna Total y valor', 'Total' in txt('#paper-render') and '500' in txt('#paper-render'))
    ev("closeModal('modal-preview')")
    ev("ventaMonth=new Date(2026,8,1); openVentasSheet()"); wait(400)
    fila=ev("[...document.querySelectorAll('#venta-sheet-body tr')].map(r=>r.innerText.replace(/\\s+/g,' ')).find(t=>t.includes('blusa 500 efectivo'))")
    ok('planilla: CC muestra el texto y guiones en cant/unit/total', fila and ' - - -' in fila.replace('arreglo cc','').replace('\t',' ') or (fila and fila.count('-')>=3))
    # layout: producto en una sola linea en escritorio
    ev("openClienteDetail('c1')"); wait()
    ev("openDocModal('venta')"); wait(100)
    ys=ev("(()=>{const r=document.querySelector('.prod-row');return [...r.querySelectorAll('input,select')].map(e=>Math.round(e.getBoundingClientRect().top))})()")
    ok('producto en una sola linea (escritorio)', max(ys)-min(ys)<=2)
    ev("closeModal('modal-doc')")
    # Edicion de filas desde la planilla (admin): saldo / pago libre y orden preservado
    if role=='admin':
        ev("openClienteDetail('c1')"); wait()
        ev("openPagoModal()"); pg.select_option('#pago-doc-select','__libre__'); pg.select_option('#pago-metodo-select','TRBF'); pg.fill('#pago-monto-input','7000'); pg.fill('#pago-fecha-input','2026-09-10'); ev("savePago()"); wait(300)
        ev("openClienteDetail('c2')"); wait()   # la ficha abierta es otra: se edita igual desde la planilla
        ev("ventaMonth=new Date(2026,8,1); openVentasSheet()"); wait(400)
        ok('planilla: saldo tiene lapiz para admin', ev("document.querySelectorAll('#venta-sheet-body .sheet-pencil').length")>=2)
        sid=ev("(ventaSheetDocsRaw.find(d=>d.esSaldoMovimiento&&d.pagos[0].monto===7000)||{}).id")
        ev(f"editSaldoFromSheet('c1','{sid}')"); wait(500)
        ok('editar saldo desde planilla abre el formulario', ev("!document.getElementById('modal-pago').classList.contains('hidden')") and ev("document.getElementById('pago-monto-input').value")=='7.000')
        pg.fill('#pago-monto-input','9000'); ev("savePago()"); wait(500)
        ok('saldo editado se ve en la planilla', '9.000' in txt('#venta-sheet-body'))
        # editar una venta desde la planilla no cambia su posicion
        orden=ev("[...document.querySelectorAll('#venta-sheet-body tr')].map(r=>r.innerText.replace(/\\s+/g,' ').slice(0,30))")
        vv=ev("ventaSheetDocsRaw.find(d=>!d.esSaldoMovimiento && d.codigo && d.codigo!=='-')")
        if vv:
            ev(f"editSheetDoc('{vv['clienteId']}','{vv['id']}','venta')"); wait(400)
            ev("saveDoc()"); wait(500); ev("closeModal('modal-preview')")
            orden2=ev("[...document.querySelectorAll('#venta-sheet-body tr')].map(r=>r.innerText.replace(/\\s+/g,' ').slice(0,30))")
            ok('editar desde planilla conserva el orden', orden==orden2)
    # XSS: nombre con HTML no debe inyectar elementos
    ev("openClientaModal()"); wait(100)
    pg.fill('#clienta-nombre','<img src=x id=xss1>'); pg.fill('#clienta-apellido','Q"><b id=xss2>'); pg.fill('#clienta-telefono','1'); pg.fill('#clienta-dni','123')
    ev("saveClienta()"); wait(300)
    ok('XSS: no se inyecta HTML', not ev("!!document.getElementById('xss1')||!!document.getElementById('xss2')"))
    ok('XSS: el texto se ve literal', '<img' in txt('#client-header-box'))
    # doble clic en Guardar venta Belgrano -> una sola venta
    ev("openDocModal('venta')"); wait(100)
    pg.fill('#doc-fecha','2026-09-05'); pg.fill('.pd-desc','doble'); pg.fill('.pd-cant','1'); pg.fill('.pd-valorunit','1000')
    ev("document.querySelector('.pd-valorunit').dispatchEvent(new Event('input'))")
    ev("addPagoRow(); document.querySelector('#pagos-container select').value='EFVO_ARS'; document.querySelector('#pagos-container input').value='1.000'; document.querySelector('#pagos-container input').dispatchEvent(new Event('input'))")
    ev("saveDoc(); saveDoc();"); wait(500)
    ok('doble clic: una sola venta', ev("docsCache.filter(d=>d.tipo==='venta'&&(d.productos||[]).some(p=>p.desc==='doble')).length")==1)
    ev("doLogout()"); wait(100)
    for r in res: print(*r)
    print('ERRORS',errs); b.close()
