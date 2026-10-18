function Pandoc(doc)
  local contents = {pandoc.Header(1, 'Contents')}
  doc:walk({Header = function(h)
    if h.level <= 2 then
      table.insert(contents, pandoc.Para({pandoc.Link(h.content, '#' .. h.identifier)}))
    end
  end})
  return doc:walk({
    RawBlock = function(el)
      if el.format == 'latex' and el.text:match('^\\clearpage') then
        return pandoc.RawBlock('openxml', '<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
      elseif el.format == 'latex' and el.text:match('^\\tableofcontents') then
        return contents
      elseif el.format == 'latex' then
        return {}
      end
    end,
    Para = function(p)
      if pandoc.utils.stringify(p):match('^The Switching Point') then
        return pandoc.Div({p},pandoc.Attr('',{},{{'custom-style','Title'}}))
      end
    end
  })
end
