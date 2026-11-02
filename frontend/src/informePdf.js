import { nivelEducativo } from './nivelEducativo'
import { jsPDF } from 'jspdf'
import { marked } from 'marked'

const plain = (value) => String(value ?? '').replace(/\*\*|__/g, '').replace(/\*/g, '').replace(/(^|\s)_([\s\S]*?)_(?=\s|$)/g, '$1$2').replace(/<[^>]*>/g, '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/[—–]/g, '-').replace(/→/g, ' > ')
const C = {navy:[10,54,91], gold:[255,192,0], soft:[243,193,51], muted:[73,100,123], border:[213,223,232], pale:[243,246,249], white:[255,255,255], amber:[255,248,223]}

export function crearInformePdf(sesion) {
  const pdf = new jsPDF({unit:'mm',format:'a4'})
  const left=18, width=174, bottom=275
  let y=0
  const drawText=(value,x,top,size=10,bold=false,color=C.navy)=>{
    pdf.setFont('helvetica',bold?'bold':'normal');pdf.setFontSize(size);pdf.setTextColor(...color)
    pdf.text(plain(value),x,top)
  }
  const lines=(value,w,size=10,bold=false)=>{
    pdf.setFont('helvetica',bold?'bold':'normal');pdf.setFontSize(size)
    return pdf.splitTextToSize(plain(value),w)
  }
  function frame(first=false) {
    pdf.setFillColor(...C.navy);pdf.rect(0,0,210,first?39:26,'F')
    drawText('trazo.',left,first?16:15,first?21:15,true,C.white)
    drawText('EVALUACIÓN GRAFOMOTORA',137,15,8,false,C.white)
    // Encabezado alineado al margen derecho.
    pdf.setFillColor(...C.gold);pdf.rect(left,first?31:21,18,1.5,'F')
    if(first)drawText('Informe para el docente',left,26,11,false,C.white)
    y=first?49:36
  }
  function newPage(){pdf.addPage();frame()}
  function ensure(h){if(y+h>bottom)newPage()}
  function paragraph(value,{size=10,color=C.navy,bold=false,gap=4,indent=0}={}){
    const wrapped=lines(value,width-indent,size,bold);const step=size*.47
    for(const line of wrapped){ensure(step);drawText(line,left+indent,y,size,bold,color);y+=step}
    y+=gap
  }
  function section(title,body,{warning=false,number=null}={}){
    const wrapped=body.flatMap((v)=>lines(v,width-16,9.5));const h=17+wrapped.length*4.6
    if(h>bottom-40){ensure(24);paragraph(title,{bold:true,size:12});body.forEach((v)=>paragraph(v,{size:9.5}));return}
    ensure(h+6)
    pdf.setFillColor(...(warning?C.amber:C.pale));pdf.roundedRect(left,y,width,h,2,2,'F')
    if(warning){pdf.setFillColor(...C.soft);pdf.rect(left,y,1.2,h,'F')}
    const x=left+8
    drawText(number?`${number}  ${title}`:title,x,y+8,11,true)
    let top=y+15
    for(const line of wrapped){drawText(line,x,top,9.5,false,warning?C.navy:C.muted);top+=4.6}
    y+=h+6
  }
  pdf.setProperties({title:`Informe grafomotor - ${sesion.child_id}`,author:'Trazo'})
  frame(true)
  // Alinear el rótulo del encabezado sin depender del largo del texto.
  pdf.setFillColor(...C.navy);pdf.rect(105,6,100,14,'F');drawText('EVALUACIÓN GRAFOMOTORA',137,15,8,false,C.white)
  paragraph(sesion.nombre_nino||sesion.child_id,{size:19,bold:true,gap:2})
  paragraph(`Código: ${sesion.child_id}    |    Edad: ${Math.floor(sesion.edad_meses/12)} años y ${sesion.edad_meses%12} meses${sesion.fecha_evaluacion?`    |    Fecha: ${sesion.fecha_evaluacion.split('-').reverse().join('/')}`:''}`,{size:8.5,color:C.muted,gap:7})
  const resumen=sesion.panel_tecnico.resumen
  const pendientes=sesion.figuras.filter((f)=>f.decision==='revisar'&&f.puntaje_docente==null)
  const educativo = nivelEducativo(resumen.percentil)
  ensure(31)
  pdf.setDrawColor(...C.border);pdf.roundedRect(left,y,width,26,2,2,'S')
  drawText(pendientes.length?'RESULTADO PROVISIONAL':'RESULTADO',left+7,y+7,8,false,C.muted)
  drawText(educativo ? `${educativo.letra} - ${educativo.nivel}` : 'Sin equivalencia',left+7,y+18,14,true)
  pdf.line(119,y+5,119,y+21);pdf.line(155,y+5,155,y+21)
  drawText(`${resumen.PD}/15`,126,y+13,16,true);drawText('Puntos',126,y+20,8,false,C.muted)
  drawText(resumen.percentil??'-',162,y+13,16,true);drawText('Percentil',162,y+20,8,false,C.muted)
  y+=33
  const tokens=marked.lexer(sesion.informe_docente_md||'')
  let heading=null,body=[],number=0
  const flush=()=>{if(heading){section(heading,body,{number:String(++number).padStart(2,'0')});heading=null;body=[]}}
  for(const token of tokens){
    if(token.type==='heading'){flush();if(token.depth!==2)heading=token.text}
    else if(token.type==='blockquote'){flush();section(pendientes.length?`${pendientes.length} figuras requieren revisión`:'Aviso del sistema',[token.text],{warning:true})}
    else if(token.type==='paragraph'){
      if(heading)body.push(token.text)
      else if(token.text.startsWith('_')||token.text.startsWith('*Este informe')){flush();y+=2;paragraph(token.text,{size:8,color:C.muted,gap:4})}
      else paragraph(token.text,{size:10,gap:6})
    }
    else if(token.type==='list'){for(const item of token.items){if(heading)body.push(`- ${item.text}`);else paragraph(`- ${item.text}`)}}
    else if(token.type==='hr')flush()
  }
  flush()
  newPage()
  paragraph('Detalle de las figuras',{size:18,bold:true,gap:3})
  paragraph('Registro de resultados por figura',{size:9,color:C.muted,gap:7})
  function tableHeader(){
    pdf.setFillColor(...C.navy);pdf.roundedRect(left,y,width,10,1,1,'F')
    drawText('FIGURA',left+5,y+6.5,8,true,C.white);drawText('RESULTADO',112,y+6.5,8,true,C.white);drawText('REVISIÓN DOCENTE',156,y+6.5,7.5,true,C.white);y+=10
  }
  tableHeader()
  for(const [i,f] of sesion.figuras.entries()){
    const pending=f.decision==='revisar'&&f.puntaje_docente==null
    const achieved=(f.puntaje_docente??f.puntaje)===1
    const label=pending?'Por revisar':achieved?'Lograda':'Necesita apoyo'
    const names=lines(`${Number(f.figura_id.slice(1))}. ${f.nombre}`,82,9)
    const h=Math.max(10,names.length*4.5+5)
    if(y+h>bottom){newPage();tableHeader()}
    pdf.setFillColor(...(i%2===0?C.pale:C.white));pdf.rect(left,y,width,h,'F')
    names.forEach((line,n)=>drawText(line,left+5,y+7+n*4.5,9))
    pdf.setFillColor(...(pending||!achieved?C.amber:[231,241,234]));pdf.roundedRect(110,y+3,39,6,1,1,'F');drawText(label,113,y+7.2,8)
    drawText(f.puntaje_docente!=null?'Confirmada':'-',158,y+7,8,false,C.muted)
    y+=h
  }
  y+=9
  paragraph('Este informe es una ayuda para el docente, no un diagnóstico. La decisión final corresponde a un profesional.',{size:8,color:C.muted})
  const pages=pdf.getNumberOfPages()
  for(let page=1;page<=pages;page++){
    pdf.setPage(page);pdf.setDrawColor(...C.border);pdf.line(left,282,192,282)
    drawText('TRAZO / Informe grafomotor',left,288,8,false,C.muted)
    drawText(`${page} / ${pages}`,182,288,8,false,C.muted)
  }
  return pdf
}
export function descargarInformePdf(sesion){
  const code=String(sesion.child_id).replace(/[^a-zA-Z0-9_-]/g,'_').slice(0,60)
  crearInformePdf(sesion).save(`Informe_${code}_${sesion.id}.pdf`)
}
