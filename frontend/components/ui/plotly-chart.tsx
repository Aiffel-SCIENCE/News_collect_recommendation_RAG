import React, { useEffect, useRef } from "react"

interface PlotlyChartProps {
  htmlContent: string
}

const PlotlyChart: React.FC<PlotlyChartProps> = ({ htmlContent }) => {
  const chartRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const chartDiv = chartRef.current
    if (!chartDiv || !htmlContent) return

    const tempDiv = document.createElement("div")
    tempDiv.innerHTML = htmlContent

    const scripts = Array.from(tempDiv.querySelectorAll("script"))
    const nonScriptNodes = Array.from(tempDiv.childNodes).filter(
      node => node.nodeName.toUpperCase() !== "SCRIPT"
    )

    chartDiv.innerHTML = ""
    nonScriptNodes.forEach(node => {
      chartDiv.appendChild(node.cloneNode(true))
    })

    scripts.forEach(script => {
      const newScript = document.createElement("script")
      Array.from(script.attributes).forEach(attr => {
        newScript.setAttribute(attr.name, attr.value)
      })
      newScript.innerHTML = script.innerHTML
      chartDiv.appendChild(newScript)
    })
  }, [htmlContent])

  return <div ref={chartRef} />
}

export default PlotlyChart 